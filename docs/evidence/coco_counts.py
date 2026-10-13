"""
Independent count to check the endpoint against, read straight from the COCO
annotation file for the images that were uploaded to the task.

Two numbers per category:
- objects: COCO annotations;
- shapes:  rows CVAT creates on "COCO 1.0" import. A non-crowd object whose
           segmentation has several polygons becomes one polygon shape per part;
           a crowd (RLE) object becomes one mask.

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

    objects, shapes = Counter(), Counter()
    for a in coco["annotations"]:
        if a["image_id"] not in image_ids:
            continue
        name = categories[a["category_id"]]
        objects[name] += 1
        shapes[name] += 1 if a["iscrowd"] else len(a["segmentation"])

    print(f"images={len(image_ids)} objects={sum(objects.values())} shapes={sum(shapes.values())}")
    print("category\tobjects\tshapes")
    for name, count in sorted(shapes.items(), key=lambda item: (-item[1], item[0])):
        print(f"{name}\t{objects[name]}\t{count}")


if __name__ == "__main__":
    main()
