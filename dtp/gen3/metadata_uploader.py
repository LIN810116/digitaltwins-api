import json
import time

from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission


class MetadataUploader(object):
    """
    Class for Gen3 submission
    """

    def __init__(self, endpoint, credentials):
        """
        Constructor

        :param endpoint: Gen3 root URL
        :type endpoint: str
        :param credentials: Path to a Gen3 credentials file
        :type credentials: str
        """
        self._endpoint = endpoint
        self._credentials = credentials

        self._auth = Gen3Auth(endpoint, refresh_file="gen3_ctt_credentials.json")
        self._submission = Gen3Submission(endpoint, self._auth)

        self._MAX_ATTEMPTS = 10

    def submit(self, program, project, record, count):
        if count >= self._MAX_ATTEMPTS:
            raise ValueError("Too many submissions")
        try:
            self._submission.submit_record(program, project, record)
        except Exception as e:
            time.sleep(2)
            self.submit(program, project, record, count + 1)


    def execute(self, program, project, file):
        """
        Submitting metadata to Gen3

        :param program: Program name
        :type program: str
        :param project: Project name
        :type project: str
        :param file: Path to the metadata file
        :type file: str
        :return:
        :rtype:
        """
        with open(file, 'r') as f:
            record = json.load(f)

        # self._submission.submit_record(program, project, record)

        self.submit(program, project, record, count=0)


