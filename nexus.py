import shutil
from base64 import b64encode

import requests

class HttpError(Exception):
    def __init__(self, response, message=""):
        """Represents an HttpError
           Get the error using attribute:
               - response.status_code
        """
        super().__init__()
        self.response = response
        self.message = message

    def __str__(self):
        return "HttpError(%s, %s)" % (self.response.status_code, self.message)

class NexusFiles(list):
    """
        A list of Nexus files, with utility functions to filter out things
    """

    def __init__(self, nexus, files=None):
        list.__init__(self)
        self.nexus = nexus

        files = files or []

        for f in files:
            if isinstance(f, NexusFile):
                self.append(f)
            else:
                raise RuntimeError(f"Wrong file type found: {f}")

    def Filter(self, folder_name=None, name=None, ends_with=None, not_ends_with=None, folder_starts_with=None):
        """Filter this list of NexusFiles and returns a new NexusFiles list
           such that it is possible to chain them
        """

        files = list(self)

        if folder_name:
            files = [x for x in files if x.folder_name == folder_name]

        if folder_starts_with:
            files = [x for x in files if x.folder_name.startswith(folder_starts_with)]

        if name:
            files = [x for x in files if x.name == name]

        if ends_with:
            files = [x for x in files if x.name.endswith(ends_with)]

        if not_ends_with:
            files = [x for x in files if not x.name.endswith(not_ends_with)]

        return NexusFiles(self.nexus, files)

    def latest(self):
        files = list(self)
        files.sort(key=lambda x: x.js.get("lastModified"), reverse=True)
        if files:
            return files[0]

        return None

    def delete(self):
        """
            delete all files of this list from the repository
        """
        for nexusFile in self:
            nexusFile.delete()

class NexusFile:
    def __init__(self, nexus, repository_name, js):
        """Builds a Nexus file stub based on the metadata of Nexus

          See
            {
            "id" : "a2JvdF9yYXc6MThkZGVjY2RmYjQ5MWVjYjA2ZTk3ZjkxODcxZjZjMzU",
            "repository" : "kbot_raw",
            "format" : "raw",
            "group" : "/release-2021.08/qa",
            "name" : "release-2021.08/qa/qa:31281020c79741de07ff1f170f503f6c7280fcb5.tar.gz",
            "version" : null,
            "assets" : [ {
              "downloadUrl" : "https://nexus.konverso.ai/repository/kbot_raw/release-2021.08/qa/qa:31281020c79741de07ff1f170f503f6c7280fcb5.tar.gz",
              "path" : "release-2021.08/qa/qa:31281020c79741de07ff1f170f503f6c7280fcb5.tar.gz",
              "id" : "a2JvdF9yYXc6NGIzNzg2NTM1OTFjNjcyMjYyMzYwMTM0OWExZDJkN2Q",
              "repository" : "kbot_raw",
              "format" : "raw",
              "checksum" : {
                "sha1" : "d1315d057fbb60d7169a80e481c0263bf494d27b",
                "md5" : "0249f7cbee42a9504b05a77eaf0e3f20"
              },
              "contentType" : "application/x-gzip",
              "lastModified" : null,
              "lastDownloaded" : null,
              "uploader" : null,
              "uploaderIp" : null,
              "fileSize" : 0
            }
        """

        # Pointer to a NexusRepository instance
        self.nexus = nexus

        # Name of the repository on the file
        self.repository_name = repository_name

        # JSON of the file
        self.js = js

    def __str__(self):
        return f"NexusFile({self.js.get('path')})"

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        path = self.js.get("path")
        if not path:
            return None

        return path.rsplit("/", 1)[-1]

    @property
    def folder_name(self):
        path = self.js.get("path")
        if not path:
            return None

        return path.rsplit("/", 1)[0]

    @property
    def path(self):
        return self.js.get("path")

    @property
    def downloadUrl(self):
        return self.js.get("downloadUrl")

    def download(self, target):
        """ Download this file to the target file"""
        self.nexus.get_file(f"/{self.repository_name}/{self.path}", target)

    def delete(self):
        """
            delete this file in the repository
        """
        self.nexus.delete_file(self.downloadUrl)

class NexusRepository:

    def __init__(self, host, user, password):
        self._url = f"https://{host}"
        self._user = user
        self._password = password

    def _get_headers(self):
        return {
            'Authorization': 'Basic %s' % (b64encode(b':'.join((self._user.encode('latin1'),
                                                                self._password.encode('latin1')))).strip().decode('ascii'))
        }

    def get_file(self, repository_path, target_file_path):
        """
            path: path below the "repository", such as:
                konverso_doc-release/aa.tar.gz"
        """
        headers = self._get_headers()
        url = self._url + "/repository" + repository_path
        response = requests.get(url, headers=headers, stream=True)

        if response.status_code == 200:
            with open(target_file_path, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
        else:
            raise HttpError(response, f"Failed to load file '{repository_path}'")

        return response


    def list_assets(self, repository_name=""):
        return self.list_repository(repository_name)

    def list_repository(self, repository_name):
        """
             Runs a Nexus query such as:
               curl -u admin:admin123 -X GET 'http://localhost:8081/service/rest/v1/assets?repository=maven-central'

             Returns a list of files in the format of a NexusFile

             Note that we are using pagination on this request
        """

        nexus_files = NexusFiles(self)

        headers = self._get_headers().copy()
        headers["Accept"] = "*/*"
        headers["Content-Type"] = "application/json"

        self._list_repository_paging(headers, nexus_files, repository_name, continuationToken="")

        return nexus_files

    def delete_file(self, target_file_path):
        """
            path: full path to file to be deleted, such as:
            https://nexus.konverso.ai/.../jira_fe477f079a60bd37c45b17a1b578988d428168d7.tar.gz
        """
        headers = self._get_headers()
        response = requests.delete(target_file_path, headers=headers)
        if response.status_code == 204:
            print(f"'{target_file_path}' has been deleted")
        else:
            raise HttpError(response, f"Failed to delete file '{target_file_path}'")

        return response

    def _list_repository_paging(self, headers, nexus_files, repository_name="", continuationToken=""):

        if repository_name:
            url = self._url + f"/service/rest/v1/assets?repository={repository_name}"
        else:
            url = self._url + f"/service/rest/v1/assets"

        if continuationToken:
            url += f"&continuationToken={continuationToken}"

        response = requests.get(url, headers=headers)

        if not response.status_code == 200:
            print(f"Failed accessing URL: {url}")
            raise HttpError(response)

        js = response.json()
        for item in js.get("items"):
            nexus_files.append(NexusFile(self, repository_name, item))

        continuationToken = js.get("continuationToken")
        if continuationToken:
            self._list_repository_paging(headers, nexus_files, repository_name, continuationToken)

    def search(self, repository=None):
        """
             Runs a Nexus query such as:
               curl -X GET -H 'Content-Type: application/json' -H 'Accept: */*'
                    -u user:password https://nexus.konverso.ai/service/rest/v1/search?repository=kbot_raw

             Returns a list of files in the format of a NexusFile
        """

        headers = self._get_headers().copy()
        headers["Accept"] = "*/*"
        headers["Content-Type"] = "application/json"

        url = self._url + f"/service/rest/v1/search?repository={repository}"
        response = requests.get(url, headers=headers)

        if not response.status_code == 200:
            raise HttpError(response)
