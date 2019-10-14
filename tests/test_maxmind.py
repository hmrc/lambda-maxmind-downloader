import unittest
from maxmind import MaxmindDownloader, handler
from hamcrest import *
import os
import boto3
from moto import mock_s3
from urllib.parse import quote
import json
import requests_mock
import logging
import shutil

logging.getLogger().getEffectiveLevel()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("botocore")
logger.setLevel(level=logging.INFO)

@mock_s3
class TestLambdaHandler(unittest.TestCase):

    def setUp(self):
        self.s3_bucket = "mys3bucket"
        self.test_tar_file_name = "tests/test.tar.gz"
        self.test_zip_file_name = "tests/test1.zip"
        self.tar_file_md5 = "16534c92fd50e3ec875d42e27d4910bb"
        self.zip_file_md5 = "a12979b6d42d8fa5650fa27efeca003a"
        self.download_location = "test_output"
        os.environ["MAXMIND_LICENSE"] = "testlicense"
        os.environ["MAXMIND_S3_BUCKET"] = self.s3_bucket
        os.environ["GEOIP_REPO"] = "testgeoiprepo"
        os.environ["DOWNLOAD_LOCATION"] = self.download_location
        os.environ["GEOIP_DB_LIST"] = "test"
        os.environ["GEOIP_CSV_LIST"] = "test1"
        self.maxmind_downloader = MaxmindDownloader()

        conn = boto3.resource('s3')
        conn.create_bucket(Bucket=self.s3_bucket)


    def tearDown(self):
        if os.path.exists(self.download_location):
            shutil.rmtree(self.download_location)

    def test_config_object(self):
        assert_that(self.maxmind_downloader.maxmind_license, equal_to("testlicense"))
        assert_that(self.maxmind_downloader.geoip_repo, equal_to("testgeoiprepo"))
        assert_that(self.maxmind_downloader.maxmind_s3_bucket, equal_to(self.s3_bucket))
        assert_that(self.maxmind_downloader.download_location, equal_to(self.download_location))
        assert_that(self.maxmind_downloader.geoip_db_list, equal_to(["test"]))
        assert_that(self.maxmind_downloader.geoip_csv_list, equal_to(['test1']))

    @requests_mock.Mocker()
    def test_maxmind_fetch_file(self, m):
        test_file = open(self.test_tar_file_name, 'rb')
        m.get("https://download.maxmind.com/app/geoip_download?edition_id=test&suffix=tar.gz.md5&license_key=testlicense", text=self.tar_file_md5)
        m.get("https://download.maxmind.com/app/geoip_download?edition_id=test&suffix=tar.gz&license_key=testlicense", body=test_file)
        filename = self.maxmind_downloader.maxmind_fetch_file("test", "tar.gz")
        assert_that(filename, equal_to("{}/test.tar.gz".format(self.download_location)))

    @requests_mock.Mocker()
    def test_maxmind_lambda(self, m):
        test_tar_file = open(self.test_tar_file_name, 'rb')
        test_zip_file = open(self.test_zip_file_name, 'rb')

        m.get("https://download.maxmind.com/app/geoip_download?edition_id=test&suffix=tar.gz.md5&license_key=testlicense", text=self.tar_file_md5)
        m.get("https://download.maxmind.com/app/geoip_download?edition_id=test&suffix=tar.gz&license_key=testlicense", body=test_tar_file)
        m.get("https://download.maxmind.com/app/geoip_download?edition_id=test1&suffix=zip.md5&license_key=testlicense", text=self.zip_file_md5)
        m.get("https://download.maxmind.com/app/geoip_download?edition_id=test1&suffix=zip&license_key=testlicense", body=test_zip_file)

        handler(None, None)

        client = boto3.client("s3")
        response = client.list_objects(Bucket=self.s3_bucket)

        assert_that(response['Contents'][0]['Key'], equal_to('test1/20190101_test1.mmdb'))
        assert_that(response['Contents'][1]['Key'], equal_to('test1/20190102_test-Locations-en.csv'))
        assert_that(len(response['Contents']), equal_to(2), response['Contents'])



