import exifread
import os
import sys
from datetime import datetime

from PIL import Image
from dateutil.parser import parse, ParserError
from glob import glob

from pillow_heif import register_heif_opener
from tqdm import tqdm


def datetime_from_file_name(file_name):
    before, sep, after = file_name.partition('_')
    datetime_str = (after or before).rpartition('.')[0]
    return datetime.strptime(datetime_str, "%Y%m%d_%H%M%S")


def datetime_from_tags(key):
    return datetime.strptime(str(tags.get(key)), "%Y:%m:%d %H:%M:%S")


def partition_file_path(file_path):
    folder_path, file_name = file_path.rsplit(os.sep, 1)
    before, sep, after = file_name.partition('_')
    return after or before


if len(sys.argv) != 2:
    print("Renames photos based on time taken.\n"
          "Files will be renamed recursively.\n"
          "Usage:\n\n"
          "python rename.py [absolute path of containing folder]\n\n"
          "Tip: drag and drop desired folder onto terminal.")
    sys.exit(1)
else:
    path = sys.argv[1]

counters = {}  # Dictionary of current count for each date
datetime_object = None
_extensions = [".heic", ".jpg", ".jpeg", ".mov", ".mp4"]
extensions = []
jpeg_quality = 90
# From https://stackoverflow.com/a/10886685
for extension in _extensions:
    def either(c):
        return '[%s%s]' % (c.lower(), c.upper()) if c.isalpha() else c
    extensions.append(''.join(map(either, extension)))
pathname = f"{path}{os.sep}**{os.sep}*"
date_paths = []
file_paths = []

print("Getting file paths...")
for extension in tqdm(extensions, file=sys.stdout, colour='BLUE'):
    file_paths.extend(glob(pathname + extension, recursive=True))

print("Sorting files...")
file_paths.sort(key=lambda fp: partition_file_path(fp))
for file_path in tqdm(file_paths, file=sys.stdout, colour='BLUE'):
    folder_path, file_name = file_path.rsplit(os.sep, 1)
    with open(file_path, "rb") as f:
        try:
            tags = exifread.process_file(f) or {}
        except AssertionError:
            tags = {}

        if "Image DateTime" in tags:
            datetime_object = datetime_from_tags("Image DateTime")
        elif "EXIF DateTimeOriginal" in tags:
            datetime_object = datetime_from_tags("EXIF DateTimeOriginal")
        else:
            try:
                datetime_object = parse(file_name, ignoretz=True, dayfirst=True, yearfirst=True, fuzzy=True)
            except ParserError:
                try:
                    datetime_object = datetime_from_file_name(file_name)
                except (ValueError, TypeError):
                    if datetime_object:
                        # print(f"Attempting to use date from previous file for {file_name}")
                        pass
                    else:
                        print(f"Cannot determine date for {file_name}. Exiting...")
                        sys.exit(1)
        date_paths.append((datetime_object, file_path))

date_paths.sort()

print("Renaming files...")
heic_extns = ['.heic', '.heif']
new_paths = []
for datetime_object, file_path in tqdm(date_paths, file=sys.stdout, colour='BLUE'):
    folder_path, file_name = file_path.rsplit(os.sep, 1)
    with open(file_path, "rb") as f:
        file_extn = "." + file_name.split(".")[-1].lower()
        if file_extn in heic_extns:
            file_extn = file_extn.upper()
        elif file_extn == ".jpeg":
            file_extn = ".jpg"
        if datetime_object:
            date_formatted = datetime_object.strftime("%Y %m %b %d")
            counter = counters.get(date_formatted, 1)
            counters[date_formatted] = counter + 1

            new_file_name = f"{date_formatted} {counter:03} 01"
            new_file_path = f"{folder_path}{os.sep}{new_file_name}{file_extn}"
            if file_extn.lower() in heic_extns:
                new_paths.append((folder_path, new_file_name, file_extn))
            os.rename(file_path, new_file_path)

print("Converting to JPG...")
register_heif_opener()
for folder_path, file_name, file_extn in tqdm(new_paths, file=sys.stdout, colour='BLUE'):
    input_file_path = f"{folder_path}{os.sep}{file_name}{file_extn}"
    output_file_path = f"{folder_path}{os.sep}{file_name}.jpg"
    image = Image.open(input_file_path)
    image.save(output_file_path, quality=jpeg_quality, exif=image.getexif())
    os.remove(input_file_path)

input("Press any key to exit...")
