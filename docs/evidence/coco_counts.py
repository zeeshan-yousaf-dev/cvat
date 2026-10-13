"""
Independent count to check the endpoint against: objects per category in the
COCO annotation file, restricted to the images that were uploaded to the task.

    python3 coco_counts.py annotations/instances_val2017.json --images-dir val2017
"""

import argparse
import json
import os
from collections import Counter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("annotations")
    parser.add_argument("--images-dir", help="only count images present in this directory")
    args = parser.parse_args()

    with open(args.annotations) as f:
        coco = json.load(f)

    categories = {c["id"]: c["name"] for c in coco["categories"]}
    images = coco["images"]
    if args.images_dir:
        present = set(os.listdir(args.images_dir))
        images = [image for image in images if image["file_name"] in present]
    image_ids = {image["id"] for image in images}

    counts = Counter(
        categories[a["category_id"]] for a in coco["annotations"] if a["image_id"] in image_ids
    )
    print(f"images={len(image_ids)} total={sum(counts.values())}")
    for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"{name}\t{count}")


if __name__ == "__main__":
    main()
