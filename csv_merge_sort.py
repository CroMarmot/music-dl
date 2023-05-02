#!/usr/bin/env python
# coding=UTF-8
# Usage:
#   python3 csv_merge_sort.py csv1.csv csv2.csv csv3.csv ...

import sys
import csv
from typing import List


def csv_merge_sort(file_list: List[str]) -> None:
    headline = []
    l = []
    for csvpath in file_list:
        with open(csvpath) as csvfile:
            reader = csv.reader(csvfile, delimiter=",", quotechar='"')
            # skip first line which is title
            head = next(reader)
            if headline == []:
                headline = head
            else:
                if head != headline:
                    print(f"Error:", file=sys.stderr)
                    print(f"File [{csvpath}] head is:", file=sys.stderr)
                    print(f"\t{head}", file=sys.stderr)
                    print(f"Other File head is:", file=sys.stderr)
                    print(f"\t{headline}", file=sys.stderr)
                    sys.exit(1)

            for row in reader:
                if len(row) == len(headline):
                    l.append(row)
                else:
                    print(f"BAD LINE[{csvpath}]: ", row, file=sys.stderr)
    l = sorted(l)

    csvdata = [headline]
    for i, row in enumerate(l):
        if i == 0 or row != l[i - 1]:
            csvdata.append(row)
    writer = csv.writer(sys.stdout) # 逗号分隔, 双引号包裹
    writer.writerows(csvdata)


csv_merge_sort(sys.argv[1:])
