#!/usr/bin/env python3

from kubernetes import client, config
from kubernetes.stream import stream

def main():
    # Load the kubeconfig
    config.load_kube_config()

    # Create a Kubernetes API client
    v1 = client.CoreV1Api()

    # Define the namespace
    namespace = "informatics"

    # List all running pods in the specified namespace
    ret = v1.list_namespaced_pod(namespace)
    for pod in ret.items:
        if pod.status.phase == "Running":
            # Command to count the number of GPUs
            gpu_count_cmd = "nvidia-smi --list-gpus | wc -l"
            # Command to get memory usage of each GPU
            gpu_mem_cmd = "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits"

            try:
                # Execute commands in the pod
                gpu_count = stream(v1.connect_get_namespaced_pod_exec, pod.metadata.name, namespace,
                                   command=['/bin/sh', '-c', gpu_count_cmd],
                                   stderr=True, stdin=False,
                                   stdout=True, tty=False)

                gpu_memories = stream(v1.connect_get_namespaced_pod_exec, pod.metadata.name, namespace,
                                      command=['/bin/sh', '-c', gpu_mem_cmd],
                                      stderr=True, stdin=False,
                                      stdout=True, tty=False)

                # Process the outputs
                num_gpus = int(gpu_count.strip())
                gpu_memories = [int(x) for x in gpu_memories.split("\n") if x]
                if all(mem < 100 for mem in gpu_memories):
                    print(f"Pod {pod.metadata.name} in namespace {namespace} has {num_gpus} GPUs, all under 100MB usage")
                else:
                    pass # print(f"Pod {pod.metadata.name} in namespace {namespace} has {num_gpus} GPUs, not all under 100MB usage")

            except Exception as e:
                print(f"Error executing command in pod {pod.metadata.name}: {e}")

if __name__ == '__main__':
    main()
