import os
import pathlib
import uuid

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_str


def validate_image_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = [".jpg", ".jpeg", ".png", ".svg"]
    if ext.lower() not in valid_extensions:
        raise ValidationError("File format not supported. Please use .jpeg, .jpg, .png, or .svg.")


def validate_pdf_only_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = [".pdf"]
    if ext.lower() not in valid_extensions:
        raise ValidationError("File format not supported. Please use .pdf.")


def validate_image_file_with_pdf_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = [".jpg", ".jpeg", ".png", ".pdf"]
    if ext.lower() not in valid_extensions:
        raise ValidationError("File format not supported. Please use .jpeg, .jpg, .png, or .pdf.")


@deconstructible
class UploadToPath(object):
    """
    Inspired by: https://stackoverflow.com/a/56735054

    """

    def __init__(self, upload_to):
        self.upload_to = upload_to

    def __call__(self, instance, filename):
        return self.generate_filename(filename)

    def get_directory_name(self):
        dirname = force_str(self.upload_to)
        return os.path.normpath(dirname)

    def get_filename(self, filename):
        orginal_name = default_storage.get_valid_name(os.path.basename(filename))
        fpath = pathlib.Path(orginal_name)
        filename = force_str(uuid.uuid1()) + force_str(fpath.suffix)
        return os.path.normpath(filename)

    def generate_filename(self, filename):
        return os.path.join(self.get_directory_name(), self.get_filename(filename))
