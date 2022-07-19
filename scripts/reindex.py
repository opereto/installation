import json
import re
import time
from datetime import datetime
import importlib

required_packages = ['kubernetes']
for package in required_packages:
    if not importlib.util.find_spec(package):
        raise Exception(f'This script requires the following python packages {str(required_packages)}.')

from kubernetes import watch, client as kubernetes_client, config as kubernetes_config
from kubernetes.stream import stream

process_index_mapping = {

  "settings": {
      "index" : {
            "number_of_shards" : 5,
            "number_of_replicas" : 1,
            "refresh_interval": "1s",
	        "blocks.read_only_allow_delete": None
        }
  },
  "mappings": {
      "properties": {
        "action_md5": {
          "type": "keyword"
        },
        "actual_version": {
          "type": "keyword"
        },
        "agent": {
          "type": "text"
        },
        "duration": {
          "type": "text"
        },
        "agent_id": {
          "type": "keyword"
        },
        "cflow_id": {
          "type": "keyword"
        },
        "cmd": {
          "type": "object",
          "enabled": False
        },
        "description": {
          "type": "text"
        },
        "end_date": {
          "type": "date"
        },
        "exec_status": {
          "type": "keyword"
        },
        "id": {
          "type": "keyword"
        },
        "api_request_id": {
          "type": "keyword"
        },
        "input_md5": {
          "type": "keyword"
        },
        "item_properties": {
          "properties": {
            "direction": {
              "type": "keyword"
            },
            "editor": {
              "type": "keyword"
            },
            "example": {
              "type": "text"
            },
            "help": {
              "type": "text"
            },
            "key": {
              "type": "text"
            },
            "mandatory": {
              "type": "boolean"
            },
            "store": {
              "type": "text"
            },
            "type": {
              "type": "keyword"
            },
            "value": {
              "type": "text"
            }
          }
        },
        "mode": {
          "type": "keyword"
        },
        "modified_date": {
          "type": "date"
        },
        "name": {
          "type": "text"
        },
        "notifications": {
          "type": "object",
          "enabled": False
        },
        "operations": {
          "type": "object",
          "enabled": False
        },
        "orig_date": {
          "type": "date"
        },
        "pflow_id": {
          "type": "keyword"
        },
        "product_id": {
          "type": "keyword"
        },
        "testplan_id": {
            "type": "keyword"
        },
        "cycle_id": {
            "type": "keyword"
        },
        "s_user": {
          "type": "keyword"
        },
        "s_version": {
          "type": "keyword"
        },
        "search_tags": {
          "properties": {
            "key": {
              "type": "keyword"
            },
            "value": {
              "type": "text"
            }
          }
        },
        "service_id": {
          "type": "keyword"
        },
        "service_type": {
          "type": "keyword"
        },
        "sflow_id": {
          "type": "keyword"
        },
        "start_date": {
          "type": "date"
        },
        "summary": {
          "type": "text"
        },
        "timeout": {
          "type": "long"
        },
        "username": {
          "type": "keyword"
        }
      }
    }
}


class ProcessesReindex(object):

    def __init__(self, namespace='opereto'):
        self.namespace = namespace
        kubernetes_config.load_kube_config()
        self.v1 = kubernetes_client.CoreV1Api()

    def _print(self, message):
        print(f'\n#### {message} ####\n')

    def generate_new_index(self):
        dt = datetime.now().strftime("%Y%m%d%H%M%S")
        return f'oboxprocesses{dt}'

    def get_pods(self):
        res = self.v1.list_namespaced_pod(self.namespace)
        return [i.metadata.name for i in res.items]

    def get_pod(self, pod_name):
        resp = self.v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
        return resp

    def print_pod_log(self, pod_name, container=None):
        w = watch.Watch()
        for e in w.stream(self.v1.read_namespaced_pod_log, name=pod_name, namespace=self.namespace, container=container,
                          follow=True,
                          _preload_content=False):
            try:
                print(str(e))
            except UnicodeDecodeError:
                print(e.encode('ascii', 'ignore'))
            except Exception as e:
                print(e)

    def exec_command(self, command, podname='opereto-es-node-0'):
        cmd = [
            '/bin/bash',
            '-c',
            command]
        print(command)
        resp = stream(self.v1.connect_get_namespaced_pod_exec,
                      podname,
                      self.namespace,
                      command=cmd,
                      stderr=True, stdin=False,
                      stdout=True, tty=False)
        return resp

    def verify_single_index(self):
        cmd = 'curl localhost:9200/_cat/indices?v | grep -c oboxprocesses'
        if int(obj.exec_command(cmd).strip()[-1])>1:
            raise Exception('There are more then a single processes index, please delete redundant indexes manually and then retry.')

    def get_current_index(self):
        cmd = 'curl localhost:9200/_cat/indices?v | grep -e oboxprocesses'
        res = obj.exec_command(cmd)
        m = re.search(r'oboxprocesses\d*', res)
        if m:
            return(m.group())

    def create_new_index(self, index):
        self._print(f'Creating a new index: {index}')
        cmd = f'curl -X PUT "localhost:9200/{index}" -H \'Content-Type: application/json\' -d\'{json.dumps(process_index_mapping)}\''
        print(obj.exec_command(cmd))

    def delete_index(self, index):
        self._print(f'Please make sure to delete the old index {index} manually')
        print(f'1. Login to the ES node: kubectl exec -it opereto-es-node-0  --container elasticsearch  -n opereto -- /bin/bash')
        print(f'2. Check the processes indexes: curl localhost:9200/_cat/indices?v')
        print(f'3. Run the following to delete old index: curl -X DELETE "localhost:9200/{index}"')


    def _alias(self, index, action):

        alias = {
            "actions": [
                {action: {"index": index, "alias": "oboxprocesses"}}
            ]
        }
        cmd = f'curl -X POST "localhost:9200/_aliases" -H \'Content-Type: application/json\' -d\'{json.dumps(alias)}\''
        print(obj.exec_command(cmd))


    def add_alias(self, index):
        self._print(f'Adding alias from oboxprocesses to {index}')
        self._alias(index, 'add')

    def remove_alias(self, index):
        self._print(f'Removing alias from oboxprocesses to {index}')
        self._alias(index, 'remove')

    def reindex(self, index):
        self._print(f'Reindexing processes to {index}')
        body = {
            "source": {
                "index": "oboxprocesses",
                "query": {
                    "range": {
                        "orig_date": {
                            "gt": "now-28d"
                        }
                    }
                }
            },
            "dest": {
                "index": index
            }
        }
        cmd = f'curl -X POST "localhost:9200/_reindex" -H \'Content-Type: application/json\' -d\'{json.dumps(body)}\''
        print(obj.exec_command(cmd))


if __name__ == "__main__":
    obj = ProcessesReindex()
    obj.verify_single_index()
    new_index = obj.generate_new_index()
    current_index = obj.get_current_index()
    obj.create_new_index(new_index)
    obj.reindex(new_index)
    try:
        obj.remove_alias(current_index)
        time.sleep(3)
        obj.add_alias(new_index)
        obj.delete_index(current_index)
    except Exception as e:
        print(str(e))
        obj.add_alias(current_index)
