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

ctr = 0
extensions = [".heic", ".HEIC", ".jpg", ".JPG", ".jpeg", ".JPEG", ".mov", ".MOV", ".mp4", ".MP4"]
pathname = f"{path}{os.sep}**{os.sep}*"
paths = []
for extension in extensions:
    paths.extend(glob(pathname + extension, recursive=True))
paths.sort()

for file_path in tqdm(paths, file=sys.stdout, colour='BLUE'):
    folder_path, file_name = file_path.rsplit(os.sep, 1)
    if file_name[:3] != "IMG":
        continue
    ctr += 1
    with open(file_path, "rb") as f:
        tags = exifread.process_file(f)
        file_extension = file_name.split(".")[-1]

        if not tags or not tags.get('Image DateTime'):
            # Attempt to parse filename for date
            try:
                datetime_object = datetime.strptime(file_name, "IMG_%Y%m%d_%H%M%S." + file_extension)
            except ValueError:
                print(f"Could not rename {file_name}")
        else:
            # Get date from EXIF tag
            date_string = str(tags.get('Image DateTime'))
            datetime_object = datetime.strptime(date_string, "%Y:%m:%d %H:%M:%S")

        date_formatted = datetime_object.strftime("%Y %m %b %d")
        new_file_name = f"{date_formatted} {ctr:03} 01.{file_extension}"
        os.rename(file_path, f"{folder_path}{os.sep}{new_file_name}")

input("Press any key to exit...")
