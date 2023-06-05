test "$(uname -m) = x86_64" && wget https://kind.sigs.k8s.io/dl/v0.19.0/kind-linux-amd64 -O /usr/local/bin/kind
chmod +x /usr/local/bin/kind

cat <<'EOF'> ~/kind-config.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  # sed 's/0.0.0.0/127.0.0.1/g' -i ~/.kube/config
  apiServerAddress: "0.0.0.0"
  apiServerPort: 6443
  ipFamily: ipv4
  dnsSearch: []
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  - |
    kind: ClusterConfiguration
    metadata:
      name: config
    apiServer:
      extraArgs:
        authorization-mode: "Node,RBAC"
      certSANs:
      - "127.0.0.1"
      - "172.29.50.162"
      - "k8s.domain.com"
- role: worker
- role: worker
containerdConfigPatches:
- |-
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."localhost:32000"]
    endpoint = ["http://localhost:32000"]
EOF

mkdir -p ~/.kube

kind get kubeconfig > ~/.kube/config || kind create cluster --image kindest/node:v1.27.1 --config ~/kind-config.yaml

sed 's/0.0.0.0/127.0.0.1/g' -i ~/.kube/config

test "$(uname -m) = x86_64" && wget https://dl.k8s.io/release/v1.27.1/bin/linux/amd64/kubectl -O /usr/local/bin/kubectl
chmod +x /usr/local/bin/kubectl

curl -fsSL https://get.helm.sh/helm-v3.8.1-linux-amd64.tar.gz | \
  sudo tar zxvf - -C "/usr/local/bin" linux-amd64/helm --strip-components 1

kubectl cluster-info
kubectl get nodes

kubectl apply -f registry.yaml

kubectl -n default port-forward deployment/registry 32000:5000
docker pull httpd
docker tag httpd localhost:32000/httpd
docker push localhost:32000/httpd


######################################################################
### Test Deployment
kubectl create deployment httpd --image=localhost:32000/httpd --port=80 \
  --dry-run=client -o yaml > httpd.yaml

kubectl apply -f httpd.yaml

kubectl expose deployment httpd --type=NodePort --port=80 --name=httpd \
  --dry-run=client -o yaml > httpd-svc.yaml

kubectl apply -f httpd-svc.yaml

NODE_PORT=$(kubectl describe service httpd | grep ^NodePort | grep -Eo '[0-9]*')
NODE_IP=$(kubectl get pod -l app=httpd -o jsonpath='{.items[0].status.hostIP}')

curl -fsSL $NODE_IP:$NODE_PORT

kubectl get pods -A

kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl -n ingress-nginx get pod -o wide --watch

cat <<EOF> test-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: test-ingress
spec:
  ingressClassName: nginx
  defaultBackend:
    service:
      name: httpd
      port:
        number: 80
EOF

kubectl apply -f test-ingress.yaml

curl http://localhost
curl https://localhost -k
curl http://$NODE_IP
curl https://$NODE_IP -k

kubectl delete -f test-ingress.yaml
######################################################################

#############################################################################
#### OpenEBS Docker
docker run -d --rm --name nfs-server \
  --net=kind \
  --privileged \
  -v $PWD/nfsroot:/nfsroot \
  -e CUSTOM_EXPORTS_CONFIG="/nfsroot *(fsid=0,rw,async,no_subtree_check,root_squash,anonuid=65534,anongid=65534)" \
  -e SHARED_DIRECTORY=/nfsroot \
  -e FILEPERMISSIONS_UID=65534 \
  -e FILEPERMISSIONS_GID=65534 \
  -e FILEPERMISSIONS_MODE=775 \
  openebs/nfs-server-alpine:0.10.0

#### NFS Directories
docker exec -it kind-control-plane bash -c "
mount -t nfs4 nfs-server:/ /mnt
mkdir --mode=775 /mnt/airflow-dags /mnt/airflow-logs
umount /mnt"

ls -lh nfsroot
#############################################################################

helm repo add csi-driver-nfs \
  https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts \
  --force-update

helm install csi-driver-nfs csi-driver-nfs/csi-driver-nfs \
  --namespace kube-system \
  --set driver.mountPermissions=0770 \
  --set controller.runOnControlPlane=false \
  --set controller.replicas=1 \
  --version v4.2.0
#############################################################################

kubectl apply -f mysql.yaml

kubectl get pods
kubectl get pods -l app=mysql -o jsonpath='{.items[0].metadata.name}' | read mysql_pod

kubectl exec -it $mysql_pod -- mysql -h mysql.default.svc.cluster.local -uairflow -pairflow -e "show databases"

kubectl apply -f namespace.yaml -f secrets.yaml -f configmap.yaml -f volumes.yaml

kubectl get pv | grep -e dags -e logs

kubectl apply -f alpine.yaml

kubectl -n airflow logs deployments/alpine

kubectl delete -f alpine.yaml

kubectl -n default port-forward deployment/registry 32000:5000


docker build \
  --pull \
  --build-arg PYTHON_BASE_IMAGE="python:3.10-slim-bullseye" \
  --build-arg AIRFLOW_VERSION="2.6.1" \
  --build-arg AIRFLOW_EXTRAS="cncf.kubernetes,mysql" \
  --build-arg ADDITIONAL_AIRFLOW_EXTRAS="" \
  --build-arg ADDITIONAL_PYTHON_DEPS="" \
  --tag "apache/airflow:2.6.1-python3.10" \
  --progress=plain \
  github.com/apache/airflow#v2-6-stable

docker build -t airflow:2.6.1 --progress=plain .

docker tag airflow:2.6.1 localhost:32000/airflow:latest
docker push localhost:32000/airflow:latest

kubectl apply -f airflow.yaml

kubectl -n airflow get pod -o wide --watch

kubectl -n airflow logs deployments/airflow -f

NODE_PORT=$(kubectl -n airflow describe service airflow | grep ^NodePort | grep -Eo '[0-9]*')
NODE_IP=$(kubectl -n airflow get pod -l app=airflow -o jsonpath='{.items[0].status.hostIP}')

echo http://$NODE_IP:$NODE_PORT

kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

kubectl -n ingress-nginx get pod -o wide --watch

cat <<EOF> airflow-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: airflow-ingress
  namespace: airflow
spec:
  ingressClassName: nginx
  defaultBackend:
    service:
      name: airflow
      port:
        number: 8080
EOF

kubectl apply -f airflow-ingress.yaml

https://localhost

kubectl -n airflow get pods -l app=airflow -o jsonpath='{.items[0].metadata.name}' | read airflow_pod

kubectl cp example_kubernetes_executor.py airflow/$airflow_pod:/opt/airflow/dags
kubectl cp test_dag_k8s.py airflow/$airflow_pod:/opt/airflow/dags

#########################################################
docker stop nfs-server
kind delete cluster
sudo rm -rf nfsroot
#########################################################

