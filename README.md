# dell-bgp-vrf
Para uma maior flexibilidade e domínio sobre as métricas fornecidas pelo os10, a criação de um agente customizado é a melhor alternativa de monitoração BGP em VRFs. Com esta solução, a obtenção de outras informações vitais para o completo gerenciamento das informações de BGP, poderá ser efetuada de modo mais granular (como situações de flapping, por exemplo), se necessário.

## 1. Requirements
Garanta que a versão do python seja igual ou superior à 3.9. Instale "sshpass" e carregue os módulos cliente do prometheus:  
	# sudo pip3 install prometheus_client  
	# sudo apt-get install sshpass  
Caso o Linux seja diferente do Ubuntu, verifique como instalar sshpass. 


## 2. Criação de Serviço no Agente

copie prometheus-dell-bgp-exporter.py para /usr/local/bin:  
	# sudo cp prometheus-dell-bgp-exporter.py  /usr/local/bin  
   
copie o arquivo de configuração para /etc/default:  
	# sudo cp prometheus-dell-bgp-exporter.yaml  /etc/default  
  
copie prometheus-dell-bgp-exporter.service para  /etc/systemd/system:  
	# sudo cp prometheus-dell-bgp-exporter.service  /etc/systemd/system  
   
realize a recarga da nova configuração:  
  	# sudo systemctl  daemon-reload  
  
inicie o  novo serviço:  
	# sudo systemctl start  prometheus-dell-bgp-exporter 
   
verifique seu status:  
	# sudo systemctl status prometheus-dell-bgp-exporter  
  
habilite o serviço para ser inicializado durante o reboot:  
	# sudo systemctl enable prometheus-dell-bgp-exporter  


## 3. Alterações do arquivo de configuração no Agente
O arquivo de configuração do agente ("/etc/default/prometheus-dell-bgp-exporter.yaml") precisa ser alterado para se ajustar ao prometheus rodando em ambiente de produção. O atual conteúdo possui as seguintes linhas:

device:  
&nbsp;&nbsp;host: 10.251.80.1  
&nbsp;&nbsp;user: admin  
&nbsp;&nbsp;password: admin  
  
exporter:  
&nbsp;&nbsp;port: 8081  
&nbsp;&nbsp;timeout: 120  

host: altere para o endereço do equipamento onde serão feitas as pesquisas do bgp/vrf  
user: utilize um usuário do dell os (apenas de pesquisa) não há necessidade de ser admin (vide o item 5. Observações Finais)  
password: e a password deste usuário  
port: defina uma porta tcp onde o agente deverá ficar em "listenning", esperando por consultas vindas do prometheus server  
timeout: intervalo que o agente utiliza para gerar informações atualizadas das métricas de bgp  
  
  
## 4. Alterações do arquivo de configuração no Prometheus server:
Para que o prometheus possa consultar o novo agente, é necessário que o arquivo de configuração "prometheus.yml" seja atualizado.
Abaixo, segue um exemplo que pode ser utilizado, ressaltando que alguns valores precisariam de alteração:

&nbsp;- job_name: os10_network_switch  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;static_configs:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- targets:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- 10.251.80.1  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;relabel_configs:  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- source_labels: [__address__]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;target_label: __param_target  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- source_labels: [__param_target]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;target_label: instance  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- target_label: __address__  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;replacement: 127.0.0.1:8081  

target: endereço do equipamento dell final, onde são realizadas as consultas pelo agente  
replacement: endereço onde o agente customizado esteja sendo executado, incluindo a porta tcp que o agente está em "listenning" (deve ser a mesmo valor que o utilizado no arquivo de configuração do agente)  



## 5. Observações Finais
É importante que antes do serviço no agente ser habilitado, o comando "ssh" seja executado manualmente no agente, para acesso ao equipamento dell, utilizando o mesmo usuário e senha descritos no item 3. Alterações do arquivo de configuração no Agente




