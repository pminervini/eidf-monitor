#!/usr/bin/env python3

from utils import get_pods_not_using_gpus

def main():
    res: list[dict] = get_pods_not_using_gpus(namespace='informatics')
    for entry in res:
        print(f'Pod {entry["pod"]} from {entry["namespace"]} was allocated {entry["num_gpus"]} but it is not using them.')

if __name__ == '__main__':
    main()
