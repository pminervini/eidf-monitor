import subprocess
import json
from datetime import datetime
from kubernetes import client, config
from kubernetes.stream import stream

def get_pods_info():
    cmd = "kubectl get pods -n informatics -o json"
    result = subprocess.run(cmd.split(), capture_output=True, text=True)
    return json.loads(result.stdout)

def get_pods_command():
    pods_info = get_pods_info()
    pod_cmd, pod_runtime, pod_numgpus = {}, {}, {}
    for item in pods_info['items']:
        pod_name = item['metadata']['name']
        containers = item['spec']['containers']

        try:
            start_time = datetime.fromisoformat(item['status']['startTime'].rstrip("Z"))
            runtime_duration = str(datetime.now() - start_time)
        except: 
            runtime_duration = '-1.'

        total_cpu = 0
        total_gpu = 0
        command = 'None'

        for container in containers:
            resources = container.get('resources', {})
            requests = resources.get('requests', {})
            limits = resources.get('limits', {})

            cpu = requests.get('cpu', "0")
            gpu = limits.get('nvidia.com/gpu', "0")

            total_cpu += int(cpu[:-1]) if 'm' in cpu else int(cpu) * 1000
            total_gpu += int(gpu)
            if 'command' in container:
                command = ' '.join(container['command'])
            if 'args' in container:
                command += ' '
                command += ' '.join(container['args'])
        pod_cmd.update({pod_name: command})
        pod_runtime.update({pod_name: runtime_duration})
        pod_numgpus.update({pod_name: total_gpu})
    return pod_cmd, pod_runtime, pod_numgpus
        
def filter_while_true_pods():
    pod_cmd, pod_runtime, pod_numgpus = get_pods_command()
    while_true_pods = []
    for k, v in pod_cmd.items():
        if 'sleep infinity' in v or 'while true' in v:
            while_true_pods.append({
                'name': k, 'command': v, 'runtime': pod_runtime[k], '#GPUs': pod_numgpus[k]
            })
    return while_true_pods

def get_pods_not_using_gpus(namespace: str = "informatics") -> list[dict]:
    config.load_kube_config()

    # Create a Kubernetes API client
    v1 = client.CoreV1Api()

    res = []

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
                    if num_gpus > 0:
                        entry = {
                            'pod': pod.metadata.name,
                            'namespace': namespace,
                            'num_gpus': num_gpus
                        }
                        res += [entry]

            except Exception as e:
                print(f"Error executing command in pod {pod.metadata.name}: {e}")
    return res
