# -*- coding: utf-8 -*-

from multiprocessing.pool import ThreadPool

from pyramid.renderers import render
from pyramid.view import view_config
import abc
import os
import boto3
import random
import shutil
import time
from s3.utils import FileUtils
from s3.utils.mailer import send_mail


class Backup(FileUtils):
    __metaclass__ = abc.ABCMeta

    def __init__(self, HomeDir='', ConfigDir='', ExcludeDirs=None, OnlyDirs=None):
        self.files = []

        self.exclude_dirs = ExcludeDirs
        self.only_dirs = OnlyDirs

        self.home_dir = HomeDir + os.sep
        self.config_dir = ConfigDir + os.sep
        self.reports_dir = self.config_dir + 'reports' + os.sep
        self.history_dir = self.config_dir + 'history' + os.sep
        self.objects_dir = self.config_dir + 'objects' + os.sep

        self.key = self.generate_hash(HomeDir)
        self.index_file = '.index_' + self.key
        self.index_file_tmp = '.index_tmp_' + self.key
        self.index_file_uploaded = '.index_uploaded_' + self.key
        self.index_file_uploaded_digest = '.index_uploaded_digest_' + self.key

    def is_lock(self):
        return self.file_exists(self.config_dir + '.lock_' + self.key)

    def lock(self):
        self.file_create(self.config_dir, '.lock_' + self.key, '')

    def unlock(self):
        if self.is_lock():
            os.remove(self.config_dir + '.lock_' + self.key)

    def write_tmp(self, files):
        # old files
        exists_files = self.file_to_list(self.config_dir + self.index_file_tmp)
        # merge and remove duplicates
        files = self.merge_list_unique(exists_files, files)
        # write tmp files
        self.file_create(self.config_dir, self.index_file_tmp, '\n'.join(files))

    def read_tmp(self):
        return self.file_to_list(self.config_dir + self.index_file_tmp)

    def clear_tmp(self):
        self.file_create(self.config_dir, self.index_file_tmp, '')

    def write_uploaded(self, files):
        exists_files = self.file_to_list(self.config_dir + self.index_file_uploaded)
        files = self.merge_list_unique(exists_files, files)
        self.file_create(self.config_dir, self.index_file_uploaded, '\n'.join(files))

    def read_uploaded(self):
        return self.file_to_list(self.config_dir + self.index_file_uploaded)

    def clear_uploaded(self):
        self.file_create(self.config_dir, self.index_file_uploaded, '')

    def write_uploaded_digest(self, files):
        exists_files = self.file_to_list(self.config_dir + self.index_file_uploaded_digest)
        files = self.merge_list_unique(exists_files, files)
        self.file_create(self.config_dir, self.index_file_uploaded_digest, '\n'.join(files))

    def read_uploaded_digest(self):
        return self.file_to_list(self.config_dir + self.index_file_uploaded_digest)

    def clear_uploaded_digest(self):
        self.file_create(self.config_dir, self.index_file_uploaded_digest, '')

    def write_local_history(self, files):
        dest_dir = self.history_dir + time.strftime("%d_%m_%Y") + os.sep
        file_name = '.local_' + str(random.getrandbits(10))
        self.file_create(dest_dir, file_name, '\n'.join(files))

    @abc.abstractmethod
    def sync_file(self, params=None):
        """ synchronization single file """
        return

    @abc.abstractmethod
    def download(self, params=None):
        """ download """
        return

    @abc.abstractmethod
    def get_index_files(self):
        """ get all indexed files """
        return

    @abc.abstractmethod
    def get_index_digests(self):
        """ get all indexed files """
        return

    @abc.abstractmethod
    def get_content_file(self, hashname):
        """ get location index file """
        return

    @abc.abstractmethod
    def rebase(self):
        """ rebase index """
        return

    @abc.abstractmethod
    def sync(self):
        """ scan and synchronization index """
        return


class LocalBackup(Backup):
    def __init__(self, HomeDir='', ExcludeDirs=None, OnlyDirs=None, ConfigDir='.backup'):
        super(LocalBackup, self).__init__(HomeDir, ExcludeDirs=ExcludeDirs, OnlyDirs=OnlyDirs, ConfigDir=ConfigDir)

    def __index_files(self):
        if self.dir_exists(self.objects_dir):
            shutil.rmtree(self.objects_dir)
        self.files = self.scan_dir(self.home_dir, self.exclude_dirs, self.only_dirs)
        return self.files

    def __write_async(self, tup):
        i, file, hash_path = tup
        dir_name = self.generate_index_dirname(file)
        digest = self.get_file_hash(file)
        self.file_create(self.objects_dir + dir_name + os.sep, hash_path, file + '|' + dir_name + digest)
        return dir_name + hash_path

    def __write_index(self):
        inputs = []
        hash_files = self.generate_hash_dict(self.files)
        for i in range(0, len(self.files)):
            inputs.append((i, self.files[i], hash_files[i]))

        pool = ThreadPool()
        hash_files_path = pool.map(self.__write_async, inputs)

        data = '\n'.join(hash_files_path)
        self.file_create(self.config_dir, self.index_file, data)

    def sync_file(self, params=None):
        return

    def get_index_digests(self):
        return

    def get_index_files(self):
        return self.file_to_list(self.config_dir + self.index_file)

    def get_content_file(self, hashname):
        index_path = self.objects_dir + self.get_index_dirname(hashname) + os.sep + hashname[2:]
        return self.file_open(index_path)

    def download(self, params=None):
        return

    def rebase(self):
        self.__index_files()
        self.__write_index()

    def sync(self):
        self.__index_files()
        self.__write_index()


class S3Backup(Backup):
    def __init__(self, S3Bucket='', HomeDir='', ExcludeDirs=None, OnlyDirs=None, ConfigDir='.backup'):
        super(S3Backup, self).__init__(HomeDir, ExcludeDirs=ExcludeDirs, OnlyDirs=OnlyDirs, ConfigDir=ConfigDir)
        self.s3_index_file = '.index_s3'
        self.s3_index_digests = '.index_s3_digests'
        self.s3 = boto3.resource('s3')
        self.bucket = self.s3.Bucket(S3Bucket)

    def __upload_s3_digest(self):
        digests_s3 = self.get_index_digests()
        digests_uploaded = self.read_uploaded_digest()

        if digests_uploaded and len(digests_uploaded) > 0:
            self.write_uploaded_digest(digests_s3)
            self.bucket.upload_file(self.config_dir + self.index_file_uploaded_digest, self.s3_index_digests)
            self.clear_uploaded_digest()

    def __upload_s3_index(self):
        try:
            # self.bucket.objects.filter(Delimiter=''):
            files_s3 = self.get_index_files()
            files_uploaded = self.read_uploaded()

            if files_uploaded and len(files_uploaded) > 0:
                self.write_uploaded(files_s3)
                self.bucket.upload_file(self.config_dir + self.index_file_uploaded, self.s3_index_file)
                self.clear_uploaded()
                self.clear_tmp()
        except Exception as e:
            pass
        finally:
            pass

    def __download_s3_index_digests(self):
        try:
            self.bucket.download_file(self.s3_index_digests, self.config_dir + self.s3_index_digests)
        except Exception as e:
            pass

    def __download_s3_index(self):
        try:
            self.bucket.download_file(self.s3_index_file, self.config_dir + self.s3_index_file)
        except Exception as e:
            pass

    def __download_from_s3(self):
        bucket = self.bucket
        paginator = bucket.meta.client.get_paginator('list_objects')
        page_iterator = paginator.paginate(Bucket=bucket.name)
        for page in page_iterator:
            for file in page.get('Contents'):
                paths = file.get('Key').split('/')
                if len(paths) > 0:
                    if len(self.exclude_dirs) > 0 and paths[0] in self.exclude_dirs:
                        continue

                    if len(self.only_dirs) > 0 and paths[0] not in self.only_dirs:
                        continue

                # ignore s3_index file
                if self.s3_index_file in file.get('Key'):
                    continue

                # ignore s3_index_hash file
                if self.s3_index_digests in file.get('Key'):
                    continue

                # ignore history folder
                if 'history' in file.get('Key'):
                    continue

                destination = self.home_dir + file.get('Key')
                if not self.dir_exists(destination):
                    os.makedirs(os.path.dirname(destination))
                self.s3.meta.client.download_file(bucket.name, file.get('Key'), destination)

    def get_content_file(self, hashname):
        return

    def download(self, params=None):
        self.__download_from_s3()
        return

    def sync_file(self, params=None):
        self.bucket.upload_file(params['path'], params['key'])
        return

    def rebase(self):
        self.__upload_s3_index()
        self.__upload_s3_digest()
        return

    def get_index_digests(self):
        return self.file_to_list(self.config_dir + self.s3_index_digests)

    def get_index_files(self):
        return self.file_to_list(self.config_dir + self.s3_index_file)

    def sync(self):
        self.__download_s3_index()
        self.__download_s3_index_digests()
        pass


class BackupManager(FileUtils):
    def __init__(self):
        super(BackupManager, self).__init__()

    @property
    def master(self):
        return self._master

    @master.setter
    def master(self, value):
        self._master = value

    @property
    def slave(self):
        return self._slave

    @slave.setter
    def slave(self, value):
        self._slave = value

    def init(self):
        master_files = self.master.get_index_files()
        slave_files = self.slave.get_index_files()

        if len(slave_files) > 0 and len(master_files) == 0:
            # create tmp file for s3
            self.slave.write_tmp(slave_files)

    def push(self):
        master_files = self.master.get_index_files()
        slave_files = self.slave.get_index_files()

        if len(slave_files) <= 0 or len(master_files) <= 0:
            return

        files = list(set(slave_files) - set(master_files))

        # create tmp file for s3
        self.slave.write_tmp(files)

        # write local history file
        self.slave.write_local_history(files)

        self.diff()

    def diff(self):
        master_digest_files = self.master.get_index_digests()
        slave_files = self.slave.get_index_files()

        if master_digest_files is not None and len(master_digest_files) <= 0:
            return

        modified_files = []
        if len(slave_files) > 0:
            for file in slave_files:
                try:
                    content = self.slave.get_content_file(file)
                    if content:
                        meta = content.split('|')
                        digest = meta[1]
                        if digest not in master_digest_files:
                            modified_files.append(file)
                except Exception as e:
                    pass
                finally:
                    pass

            self.slave.write_tmp(modified_files)

    def pull(self):
        master_files = self.master.get_index_files()
        if len(master_files) <= 0:
            return

        self.master.download()
        self.slave.rebase()

    def rebase_digest(self):
        slave_files = self.slave.get_index_files()
        if len(slave_files) > 0:
            digests = []
            for file in slave_files:
                try:
                    content = self.slave.get_content_file(file)
                    if content:
                        meta = content.split('|')
                        digest = meta[1]
                        digests.append(digest)
                except Exception as e:
                    pass
                finally:
                    pass
            self.slave.write_uploaded_digest(digests)
            self.master.rebase()

    def apply(self):
        uploaded_files = []
        uploaded_digests = []

        # uploaded files
        uploaded_files = self.slave.read_uploaded()

        # open tmp file
        files = self.slave.read_tmp()

        if len(files) > 0:
            if len(uploaded_files) > 0:
                files = list(set(files) - set(uploaded_files))
                self.slave.clear_tmp()
                self.slave.write_tmp(files)

            size = 0
            for file in files:
                try:
                    content = self.slave.get_content_file(file)
                    if content:
                        meta = content.split('|')
                        file_path = meta[0]
                        digest = meta[1]

                        key = self.get_relative_path(self.master.home_dir, file_path)
                        self.master.sync_file({'path': file_path, 'key': key})

                        # os.path.getsize(file_path)
                        size += os.stat(file_path).st_size

                        # list of uploaded files
                        uploaded_files.append(file)
                        self.slave.write_uploaded(uploaded_files)

                        # list of digests
                        uploaded_digests.append(digest)
                        self.slave.write_uploaded_digest(uploaded_digests)
                except Exception as e:
                    pass

            self.master.rebase()

            return {
                'count': len(uploaded_files),
                'date': time.strftime("%d-%m-%Y"),
                'size': self.sizeof_fmt(size)
            }
