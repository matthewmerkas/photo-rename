import exifread
import os
import sys
from datetime import datetime
from glob import glob
from tqdm import tqdm


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
extensions = [".heic", ".HEIC", ".jpg", ".JPG", ".jpeg", ".JPEG", ".mov", ".MOV", ".mp4", ".MP4"]
pathname = f"{path}{os.sep}**{os.sep}*"
paths = []
for extension in extensions:
    paths.extend(glob(pathname + extension, recursive=True))
paths.sort()

for file_path in tqdm(paths, file=sys.stdout, colour='BLUE'):
    folder_path, file_name = file_path.rsplit(os.sep, 1)
    with open(file_path, "rb") as f:
        tags = exifread.process_file(f)
        file_extension = file_name.split(".")[-1]

        if tags and tags.get("Image DateTime"):
            # Get date from EXIF tag
            date_string = str(tags.get("Image DateTime"))
            datetime_object = datetime.strptime(date_string, "%Y:%m:%d %H:%M:%S")
        else:
            # Attempt to parse filename for date
            split = file_name.split("_", 1)
            if len(split) > 1:
                date_string = split[1]
            else:
                date_string = file_name
            try:
                datetime_object = datetime.strptime(date_string, f"%Y%m%d_%H%M%S.{file_extension}")
            except ValueError as ve:
                print(f"Attempting to use date from previous file for {file_name}")

        if datetime_object:
            date_formatted = datetime_object.strftime("%Y %m %b %d")
            counter = counters.get(date_formatted, 1)
            counters[date_formatted] = counter + 1

            new_file_name = f"{date_formatted} {counter:03} 01.{file_extension}"
            os.rename(file_path, f"{folder_path}{os.sep}{new_file_name}")

input("Press any key to exit...")
