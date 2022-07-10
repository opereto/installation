# installation

### Install helm

https://helm.sh/docs/intro/install
** make sure you are using helm version 3.5.x and above


### Step 1: install Opereto database
```console
helm install opereto-es opereto-es --namespace opereto --create-namespace
```

##### Attention: verify that ES cluster is configured properly before proceeding

### Step 2: install Opereto service
```console
helm install opereto-service opereto-service --namespace opereto --create-namespace 
```

##### Attention: verify that Opereto service cluster is up and running before proceeding


### Step 3: install Opereto ingress

See ingress_example/README.md


