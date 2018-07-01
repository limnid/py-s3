import hashlib
import os
import random
from hashlib import sha1


class FileUtils(object):
    def scan_dir(self, path, exclude_dirs=None, only_dirs=None, root_files=True):
        home_dir = path
        files = []
        for dir_name, dir_names, file_names in os.walk(path):
            if '.git' in dir_names:
                # don't go into any .git directories.
                dir_names.remove('.git')

            if '.backup' in dir_names:
                dir_names.remove('.backup')

            path = self.get_relative_path(home_dir, dir_name)
            paths = path.split('/')

            # Exclude dirs
            if len(path) > 0 and len(exclude_dirs) > 0:
                path = path.lstrip('/')
                path = path.rstrip('/')
                matches = [x for x in exclude_dirs if path.startswith(x)]
                if len(matches) > 0:
                    continue

            # Only dirs
            if len(path) > 0 and len(only_dirs) > 0:
                matches = [x for x in only_dirs if path.startswith(x)]
                if len(matches) <= 0:
                    continue

            # Ignore root files
            if not root_files and len(path) <= 0:
                if len(paths) > 0 >= len(paths[0]):
                    continue

            # print path to all subdirectories first.
            for subdirname in dir_names:
                # print(os.path.join(dir_name, subdirname))
                pass

            # print path to all filenames.
            for file_name in file_names:
                files.append(os.path.join(dir_name, file_name))
                pass

        return files

    def html_decode(self, string):
        """
        Returns the ASCII decoded version of the given HTML string. This does
        NOT remove normal HTML tags like <p>.
        """
        htmlCodes = (
            ("'", '&#39;'),
            ('"', '&quot;'),
            ('>', '&gt;'),
            ('<', '&lt;'),
            ('&', '&amp;')
        )
        for code in htmlCodes:
            string = string.replace(code[1], code[0])
        return string

    def merge_list_unique(self, list1, list2):
        files = list(list1) + list(list2)
        result = {}
        for file in files:
            result[file.strip()] = None
        return result.keys()

    def get_relative_path(self, home_dir, file_path):
        return file_path[len(home_dir):]

    def file_exists(self, path):
        return os.path.isfile(path)

    def dir_exists(self, path):
        return os.path.exists(os.path.dirname(path))

    def file_open(self, path, utf8=False):
        try:
            file = open(path, 'r')
            text = file.read()
            if utf8:
                text = text.decode('utf8')
            file.close()
            return text
        except (IOError, OSError) as e:
            return None

    def file_create(self, dir_name, file_name, data, utf8=False):
        random_hash = random.getrandbits(128)

        try:
            if not os.path.exists(os.path.dirname(dir_name + file_name)):
                os.makedirs(os.path.dirname(dir_name + file_name))
        except:
            pass

        file = open(dir_name + file_name, 'w+')
        if utf8:
            data = data.encode('utf-8')
        file.write(data)
        file.close()

    def file_append(self, dir_name, file_name, data):
        random_hash = random.getrandbits(128)
        if not os.path.exists(os.path.dirname(dir_name + file_name)):
            os.makedirs(os.path.dirname(dir_name + file_name))
        file = open(dir_name + file_name, 'r+')
        file.write(data)
        file.close()

    def file_to_list(self, path):
        file = self.file_open(path)
        return [x for x in file.split('\n')] if file else []

    def get_index_dirname(self, hashname):
        return hashname[0:2] if len(hashname) > 2 else os.sep

    def generate_index_dirname(self, filepath):
        paths = filepath.split('/')
        paths = paths[:-1]
        paths = '/'.join(paths)
        path_hash = self.generate_hash(paths)
        return self.get_index_dirname(path_hash)

    def generate_hash(self, data):
        s = sha1()
        s.update(data + "%u\0" % len(data))
        s.update(data)
        return s.hexdigest()

    def get_file_hash(self, file):
        hash_md5 = hashlib.md5()
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def generate_hash_dict(self, files):
        return [self.generate_hash(x) for x in files]

    def sizeof_fmt(self, num, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)

    def chmod(self, path, mode):
        """
        @:param path: /var/www/mode
        @:param mode: 0o777
        """
        for root, dirs, files in os.walk(path):
            for dir_name in dirs:
                os.chmod(os.path.join(root, dir_name), mode)
            for file_name in files:
                os.chmod(os.path.join(root, file_name), mode)

    def chown(self, path, uid, gid):
        """
        @:param path: /var/www/mode
        @:type uid: int
        @:type gid: int
        """
        for root, dirs, files in os.walk(path):
            for dir_name in dirs:
                os.chown(os.path.join(root, dir_name), int(uid), int(gid))
            for file_name in files:
                os.chown(os.path.join(root, file_name), int(uid), int(gid))


