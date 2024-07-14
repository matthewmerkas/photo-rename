from uuid import uuid4

import exifread
import os
import sys
from datetime import datetime, timedelta

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
    dt = datetime.strptime(str(tags.get(key)), "%Y:%m:%d %H:%M:%S")
    offset_time = str(tags.get("EXIF OffsetTimeOriginal") or tags.get("EXIF OffsetTime") or "")
    if type(offset_time) is str and len(offset_time) > 0:
        offset_exif = parse_offset(offset_time, inverse=True)  # Subtract offset to get UTC
        return dt + timedelta(minutes=offset_exif) + timedelta(minutes=offset_input)
    return dt


def parse_offset(offset: str, inverse=False):
    err_msg = f"Invalid offset '{offset}'. Using +00:00"
    if not (type(offset) is str and len(offset) > 0):
        return print(err_msg)
    if offset[0] == "+":
        multiplier = 1
    elif offset[0] == "-":
        multiplier = -1
    else:
        return print(err_msg)
    if inverse:
        multiplier *= -1
    try:
        hour, minute = offset.split(":")
        hour = int(hour)
        minute = int(minute)
    except ValueError:
        return print(err_msg)
    else:
        return (hour * 60 + minute) * multiplier


def partition_file_path(file_path):
    folder_path, file_name = file_path.rsplit(os.sep, 1)
    before, sep, after = file_name.partition('_')
    return after or before


if len(sys.argv) != 2:
    print("Renames photos based on time taken.\n"
          "Files will be renamed recursively.\n"
          "Live Photos (.mov) will be deleted.\n"
          "Usage:\n\n"
          "python rename.py [absolute path of containing folder]\n\n"
          "Tip: drag and drop desired folder onto terminal.")
    sys.exit(1)
else:
    path = sys.argv[1]

counters = {}  # Dictionary of current count for each date
datetime_object = None
deleted_count = 0
_extensions = [".heic", ".jpg", ".jpeg", ".mov", ".mp4"]
extensions = []
jpeg_quality = 90
# From https://stackoverflow.com/a/10886685
for extn in _extensions:
    def either(c):
        return '[%s%s]' % (c.lower(), c.upper()) if c.isalpha() else c
    extensions.append(''.join(map(either, extn)))
pathname = f"{path}{os.sep}**{os.sep}*"
date_paths = []
file_paths = []

_offset_input = input("Offset from UTC (+10:00): ") or "+10:00"
offset_input = parse_offset(_offset_input)

start_count = input("Start count (1): ")
try:
    start_count = int(start_count)
    if start_count < 1:
        raise ValueError
except ValueError:
    print(f"Invalid count '{start_count}'. Starting at 1")
    start_count = 1

print("Getting file paths...")
for extn in tqdm(extensions, file=sys.stdout, colour='BLUE'):
    file_paths.extend(glob(pathname + extn, recursive=True))

print("Sorting files...")
file_paths.sort(key=lambda fp: partition_file_path(fp))
for file_path in tqdm(file_paths, file=sys.stdout, colour='BLUE'):
    folder_path, file_name = file_path.rsplit(os.sep, 1)
    with open(file_path, "rb") as f:
        try:
            tags = exifread.process_file(f) or {}
        except AssertionError:
            tags = {}

        if "EXIF DateTimeOriginal" in tags:
            datetime_object = datetime_from_tags("EXIF DateTimeOriginal")
        elif "Image DateTime" in tags:
            datetime_object = datetime_from_tags("Image DateTime")
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
                        print(f"Cannot determine date for {file_name}")
                        input("Press any key to exit...")
                        sys.exit(1)
        uuid = str(uuid4())
        date_paths.append((datetime_object, folder_path, file_name, uuid))

date_paths.sort()

print("Renaming files (1/2)...")
for datetime_object, folder_path, file_name, uuid in tqdm(date_paths, file=sys.stdout, colour='BLUE'):
    os.rename(f"{folder_path}{os.sep}{file_name}", f"{folder_path}{os.sep}{uuid}")

print("Renaming files (2/2)...")
heic_extns = ['.heic', '.heif']
last_name = ""
new_paths = []
for datetime_object, folder_path, file_name, uuid in tqdm(date_paths, file=sys.stdout, colour='BLUE'):
    old_file_path = f"{folder_path}{os.sep}{uuid}"
    with open(old_file_path, "rb") as f:
        partitions = file_name.rpartition(".")
        extn = "".join(partitions[1:]).lower()
        if extn in heic_extns:
            extn = extn.upper()
        elif extn == ".jpeg":
            extn = ".jpg"
        elif extn == ".mov" and last_name == partitions[0]:
            # Live Photo
            os.remove(old_file_path)
            deleted_count += 1
            continue
        last_name = partitions[0]
        if datetime_object:
            date_formatted = datetime_object.strftime("%Y %m %b %d")
            if date_formatted not in counters:
                counters[date_formatted] = start_count
                start_count = 1
            counter = counters.get(date_formatted)
            counters[date_formatted] = counter + 1

            new_name = f"{date_formatted} {counter:03} 01"
            new_file_path = f"{folder_path}{os.sep}{new_name}{extn}"
            if extn.lower() in heic_extns:
                new_paths.append((folder_path, new_name, extn))
            os.rename(old_file_path, new_file_path)

print("Converting to JPG...")
register_heif_opener()
for folder_path, name, extn in tqdm(new_paths, file=sys.stdout, colour='BLUE'):
    input_file_path = f"{folder_path}{os.sep}{name}{extn}"
    output_file_path = f"{folder_path}{os.sep}{name}.jpg"
    image = Image.open(input_file_path)
    image.save(output_file_path, quality=jpeg_quality, exif=image.getexif())
    os.remove(input_file_path)

print(f"Deleted {deleted_count} Live Photos.")
input("Press any key to exit...")
