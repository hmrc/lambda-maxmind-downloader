#!/usr/bin/env python

import requests
import boto3
import os
import logging
import tarfile
import hashlib
import zipfile
import glob
import shutil

logger = logging.getLogger()
logger.setLevel(level=logging.INFO)


class MaxmindDownloader():

    def __init__(self):
        self.maxmind_license = os.getenv("MAXMIND_LICENSE", None)
        self.geoip_repo = os.getenv("GEOIP_REPO", "maxmind")
        self.maxmind_s3_bucket = os.getenv("MAXMIND_S3_BUCKET", None)
        self.download_location = os.getenv("DOWNLOAD_LOCATION", "output")
        self.geoip_db_list = \
            os.getenv("GEOIP_DB_LIST", "GeoIP2-ISP,"
                                       "GeoIP2-Connection-Type,"
                                       "GeoIP2-Domain,"
                                       "GeoIP2-City,"
                                       "GeoIP2-Anonymous-IP").split(',')
        self.geoip_csv_list = os.getenv("GEOIP_CSV_LIST",
                                        "GeoIP2-City-CSV").split(',')
        self.maxmind_url = "https://download.maxmind.com"

        if self.maxmind_license is None:
            raise Exception("MAXMIND_LICENSE ndeeds to be set")

        if self.maxmind_s3_bucket is None:
            raise Exception("MAXMIND_S3_BUCKET needs to be set")

    def md5(self, fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def process_maxmind_mmdb_files(self):
        for file in self.geoip_db_list:
            filename = self.maxmind_fetch_file(file, "tar.gz")
            extract_file = tarfile.open(filename)
            extract_file.extractall(path=self.download_location)

            files_to_upload = []
            location = "{}/**/*.{}".format(self.download_location, "mmdb")
            for entry in glob.glob(location):
                files_to_upload.append(entry)

            client = boto3.client("s3")
            for file in files_to_upload:
                body_data = open(file, 'rb')
                s3_path = self.generate_s3_path(file)
                logger.info("Saving {} to {}".format(file, s3_path))
                client.put_object(
                    ACL='private',
                    Body=body_data,
                    Bucket=self.maxmind_s3_bucket,
                    Key=s3_path
                )

            self.folder_cleanup()

    def process_maxmind_csv_files(self):
        logger.info("Processing csv zip files")
        for file in self.geoip_csv_list:
            filename = self.maxmind_fetch_file(file, "zip")
            z = zipfile.ZipFile(filename)
            for zip_entry in z.namelist():
                if "csv" in zip_entry and "Locations-en.csv" in zip_entry:
                    # file_info = z.getinfo(zip_entry)
                    s3_path = self.generate_s3_path(zip_entry)
                    logger.info("Saving {} to {}".format(zip_entry, s3_path))
                    s3_resource = boto3.resource('s3')
                    s3_resource.meta.client.upload_fileobj(
                        z.open(zip_entry),
                        Bucket=self.maxmind_s3_bucket,
                        Key=f'{s3_path}'
                    )
        self.folder_cleanup()

    def generate_s3_path(self, file_path):
        if self.download_location in file_path:
            target_locatiom, relative_path = \
                file_path.split(self.download_location + "/")
        else:
            relative_path = file_path

        dir, file_name = relative_path.split("/")
        edition, file_date = dir.split("_")

        s3_path = "{}/{}-{}".format(edition, file_date, file_name)

        return s3_path

    def maxmind_fetch_file(self, edition, suffix):

        # Fetching files
        logger.info("Downloading {}".format(edition))

        md5_response = requests.get("{}/app/geoip_download?"
                                    "edition_id={}&"
                                    "suffix={}.md5&"
                                    "license_key="
                                    "{}".format(self.maxmind_url,
                                                edition,
                                                suffix,
                                                self.maxmind_license))
        md5_response.raise_for_status()
        md5_sum = md5_response.text

        with requests.get("{}/app/geoip_download?"
                          "edition_id={}&"
                          "suffix={}&"
                          "license_key="
                          "{}".format(self.maxmind_url,
                                      edition,
                                      suffix,
                                      self.maxmind_license)) as r:
            r.raise_for_status()
            filename = "{}/{}.{}".format(self.download_location,
                                         edition, suffix)
            logger.info("Saving {}".format(filename))

            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                f.close()

        logger.info("Downloaded {}".format(edition))

        # Checking md5 sum of file
        file_md5 = self.md5(filename)
        if str(file_md5) != str(md5_sum):
            raise Exception("MD5 Sum of downloaded file {} does"
                            " not match, expected: {}, found: {}".
                            format(filename, str(file_md5), str(md5_sum)))

        return filename

    def folder_cleanup(self):
        shutil.rmtree(self.download_location)


def handler(event, context):
    logger.info("Downloading maxmind data files")
    maxmind_downloader = MaxmindDownloader()
    maxmind_downloader.process_maxmind_mmdb_files()
    maxmind_downloader.process_maxmind_csv_files()

    return {"message": "lambda complete"}


if __name__ == "__main__":
    handler(None, None)
