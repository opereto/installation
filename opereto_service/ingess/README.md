### Opereto Ingress

1. Allows only HTTPS (port 443)
1. Allows regexp path
1. Uses valid SSL certificates

If you are not familier with ingress yet, please read this first: [What is Ingress?](https://kubernetes.io/docs/concepts/services-networking/ingress/#what-is-ingress)
This example assumes that you installed opereto cluster using the default namespace (e.g. opereto). Otherwise, please modify the namespace in all kubectl commands and yaml files given in this example.


### Step 1: Install the ingress

Follow [Kubernetes Nginx/GKE installation guide](https://kubernetes.github.io/ingress-nginx/deploy/#gce-gke) based on your infrastructure

### Step 2: create tls secret file

* Prepare tls key and certificate files
```console
cat domainname.key > tls.key
cat domainname.crt domainname.ca-bundle > tls.crt
```

* Create the tls secret entry  
```
kubectl -n opereto create secret tls clustersecret --key /tmp/tls.key --cert /tmp/tls.crt
```


#### Step 3: Update the nginx controller and config map (nginx-ingress-controller)

**nginx controller configmap**
```console
  allow-snippet-annotations: "true"
  client-body-buffer-size: 20M
  disable-access-log: "false"
  error-log-level: error
  proxy-body-size: 20M
  proxy-buffer-size: 20M
  proxy-buffers-number: 4 5M
  proxy-read-timeout: 360s
  proxy-send-timeout: 360s
  ssl_ciphers: HIGH:!aNULL:!MD5;
  ssl_handshake_timeout: 10s
  ssl_session_cache: shared:SSL:20m
  ssl_session_timeout: 2h
  worker-processes: "8"
  
```

**nginx-ingress-controller (workload)**    
```console
spec:
      containers:
      - args:
        - /nginx-ingress-controller
        ...
        ...
        - --default-ssl-certificate=opereto/clustersecret      
```

**nginx-ingress-controller service**:
Add the external IP attached to the load balancer

```console
spec:
  ...
      loadBalancerIP: 1.1.1.1
  
```

#### Step 4:

Add more replica to ingress controller workload as needed.



### Troubleshooting

To run the ngnix in debug mode, change in nginx-ingress-controller config map:

```console
  disable-access-log: "false"
  error-log-level: "debug"
```

To display the ingress controller config:
```console
kubectl -n opereto exec ingress-nginx-controller-d76bc68bb-wgsrj -- cat nginx.conf
```

