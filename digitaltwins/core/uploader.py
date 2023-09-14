import configparser
import os
import re
import time

from pathlib import Path
import shutil

from digitaltwins import MetadataQuerier
from digitaltwins import MetadataConvertor
from digitaltwins import MetadataUploader
from digitaltwins.irods.irods import IRODS


class Uploader(object):
    def __init__(self, config_file):
        self.config_file = config_file
        self._configs = configparser.ConfigParser()
        self._configs.read(config_file)

        self._gen3_endpoint = self._configs["gen3"].get("endpoint")
        self._gen3_cred_file = Path(self._configs["gen3"].get("cred_file"))

        self._program = self._configs["gen3"].get("program")
        self._project = self._configs["gen3"].get("project")

        time_stamp = time.time()
        dirname_tmp = "./tmp_{}".format(time_stamp)
        self._dir_tmp = Path(dirname_tmp)
        self._meta_dir_tmp = self._dir_tmp.joinpath(Path("gen3_tmp"))

        self._meta_files = ["experiment.json", "dataset_description.json", "manifest.json", "subjects.json"]

        self._dataset_submitter_id_template = "dataset-12L_{id}-version-1"
        self._dataset_id_index = 2
        self._MAX_ATTEMPTS = 10

    def execute(self, dataset_dir):
        dataset_dir = Path(dataset_dir)
        self._verify_dataset(dataset_dir)

        # get dataset (submitter) id
        dataset_id = self._generate_dataset_id()

        os.makedirs(self._dir_tmp, exist_ok=True)

        dataset_dir_tmp = self._dir_tmp.joinpath(dataset_id)
        shutil.copytree(str(dataset_dir), str(dataset_dir_tmp))
        dataset_dir = dataset_dir_tmp

        # Upload metadata to Gen3
        self.upload_metadata(dataset_dir)
        # Upload the actual files to iRODS
        self.upload_dataset(dataset_dir)

        if self._dir_tmp.is_dir:
            shutil.rmtree(str(self._tmp_dataset_dir))

        print("Dataset uploaded")

    def upload_metadata(self, dataset_dir):
        meta_dir = self._meta_dir_tmp
        # convert sds metadata to gen3
        meta_convertor = MetadataConvertor(program=self._program, project=self._project, experiment=dataset_dir.name)
        meta_convertor.execute(source_dir=dataset_dir, dest_dir=meta_dir)

        # upload metadata
        meta_uploader = MetadataUploader(self._gen3_endpoint, str(self._gen3_cred_file))

        for filename in self._meta_files:
            print("Uploading: " + str(filename))
            file = meta_dir.joinpath(filename)
            meta_uploader.execute(program=self._program, project=self._project, file=str(file))

        # delete the temporary metadata dir
        if meta_dir.is_dir:
            shutil.rmtree(meta_dir)

    def upload_dataset(self, dataset_dir):
        irods = IRODS(self._configs)
        irods.upload(dataset_dir)

    def _verify_dataset(self, dataset_dir):
        if dataset_dir.is_dir():
            dataset_name = dataset_dir.name
        else:
            raise NotADirectoryError("Dataset directory not found")

        # check if dataset exists
        # todo
        pass

    def _generate_dataset_id(self, count=0):
        if count >= self._MAX_ATTEMPTS:
            raise ValueError("Max attempts {count} exceeded. Please try submitting again. If the error persists, "
                             "please contact the developers").format(count=count)
        # list datasets
        querier = MetadataQuerier(self.config_file)

        try:
            datasets = querier.get_datasets(program=self._project, project=self._project)
        except Exception:
            time.sleep(2)
            self._generate_dataset_id(count=count + 1)

        if datasets:
            datasets.sort()
            latest_dataset = datasets[-1]
            elements = re.split('_|-', latest_dataset)
            latest_id = elements[self._dataset_id_index]
            new_id = int(latest_id) + 1
            new_dataset_id = self._dataset_submitter_id_template.format(id=new_id)
        else:
            return self._dataset_submitter_id_template.format(id="1")

        return new_dataset_id
