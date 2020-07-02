#!/usr/bin/python
# coding: utf-8
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
import os
import ipdb
import time
import json
import docker
import requests
import logging
import datetime
import subprocess
from prettytable import PrettyTable
import sys
if sys.version_info < (3, 1):
    reload(sys)
    sys.setdefaultencoding('utf-8')
else:
    raw_input = input

#print('=' * 80)
#print('[INFO] Dockercon Tools Start Run')
#print('=' * 80)
#print('Python %s' % sys.version)
#ipdb.set_trace()
#---------------------- Load the configuration file --------------------------
#sys.path.append(os.path.dirname(os.path.realpath(__file__))
CONF_NAME = "dockercon.json"
ONLINE_CONF_NAME = "dockercon_online.json"
OFFLINE_CONF_NAME = "dockercon_offline.json"

def ui_load_conf(eennvv=None):
    global CONF
    if eennvv == "pro":
        CONF_FILE = "%s/%s" % (os.path.dirname(os.path.realpath(__file__)), ONLINE_CONF_NAME)
    else:
        CONF_FILE = "%s/%s" % (os.path.dirname(os.path.realpath(__file__)), OFFLINE_CONF_NAME)
    with open(CONF_FILE) as f:
        CONF = json.load(f)


def curr_time():
    #return time.strftime('%Y-%m-%d %H:%M:%S')
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')


#def get_cur_info():
#    print(sys._getframe().f_code.co_filename)
#    print(sys._getframe(0).f_code.co_name)
#    print(sys._getframe(1).f_code.co_name)
#    print(sys._getframe().f_lineno)

#---------------------- log configuration file --------------------------
#日志输出到文件
logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)-8s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                filename='/oma/deploy/scripts/log/dockercon.log',
                filemode='a')

#日志打印到屏幕
console = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


class ContainerInfo(object):
    def __init__(self, env, container_name):
        self.conf = CONF
        self.env = env
        self.container_name = container_name
        self.env_container_name_inf = self.conf[self.env]["container_inf"][self.container_name]
        self._homed_ip = self.env_container_name_inf["homed_ip"]

    def module_name(self):
        return self.env_container_name_inf["module_name"]

    def homed_ip(self):
        return self.env_container_name_inf["homed_ip"]

    def container_ip(self):
        return self.env_container_name_inf["ip"]

    def net_name(self):
        return self.env_container_name_inf["net_name"]

    def cpu(self):
        return self.env_container_name_inf.get("cpu")

    def cpu2(self):
        cpu_limit = self.env_container_name_inf.get("cpu")
        if cpu_limit:
            return " --cpuset-cpus %s " % cpu_limit
        else:
            return ""

    def memory(self):
        return self.env_container_name_inf["memory"]

    def binds(self):
        binds_list=["/etc/hosts:/etc/hosts:ro"]
        general_binds=self.conf[self.env]["general_binds"]
        custom_binds =self.env_container_name_inf.get("custom_binds")
        if general_binds != "":
            binds_list.append(general_binds)
        if custom_binds != "":
            binds_list.append(custom_binds)
        return binds_list

    def binds2(self):
        binds_str=" -v /etc/hosts:/etc/hosts:ro "
        general_binds=self.conf[self.env]["general_binds"]
        custom_binds=self.env_container_name_inf.get("custom_binds")
        if general_binds != "":
            binds_str = binds_str + " -v %s " % general_binds
        if custom_binds != "":
            binds_str = binds_str + " -v %s " % custom_binds
        return binds_str

    def nat_port(self):
        port = self.env_container_name_inf.get("nat_port")
        if port:
            #port_dict={_port:_port for _port in port.split(" ")}
            return eval(str(port))
        else:
            return

    def nat_port2(self):
        port = self.env_container_name_inf.get("nat_port")
        if port:
            port_str=" -p {0}".format(port)
            return port_str
        else:
            return ""

    def syslog_address(self):
        return self.env_container_name_inf["syslog_address"]

    def dns_server(self):
        return self.conf[self.env]["dns_server"]

    def nginx_ip(self):
        return self.conf[self.env].get("nginx_ip")

    def eureka_url(self):
        return self.conf[self.env].get("eureka_url")

    def eureka_user(self):
        return self.conf[self.env].get("eureka_user")

    def eureka_password(self):
        return self.conf[self.env].get("eureka_password")

    def eureka_appname(self):
        return self.env_container_name_inf.get("eureka_appname")

    def eureka_port(self):
        return self.env_container_name_inf.get("eureka_port")

    def service_group(self):
        return self.env_container_name_inf.get("service_group")

    def mq_gray_switch(self):
        return self.env_container_name_inf.get("mq_gray_switch")


#--- Build ---------------------------------------------------------------------------
def BUILD(env, module_name, tag):
    c = docker.DockerClient(base_url='unix://var/run/docker.sock')
    L = docker.APIClient(base_url='unix://var/run/docker.sock')
    _repository='h.cn/%s/%s'    % (env, module_name)
    image_name ='h.cn/%s/%s:%s' % (env, module_name, tag)
    build_path ='/oma/docker/dockerfile/%s/%s' % (env, module_name)
    #dockerfile ='%s/Dockerfile' % (build_path)
    ##nocache (bool) – Don’t use the cache when set to True
    build_dict ={'tag':image_name,'path':build_path,'dockerfile':'Dockerfile','nocache':True,'rm':True}
    logging.debug('Start building image %s' % (image_name))
    logging.debug('=' * 80)
    logging.debug("[INFO] Build Docker Image %s" % module_name)
    logging.debug('=' * 80)
    build_info = L.build(**build_dict)

    for i in build_info:
        for k,v in eval(i).items():
            if isinstance(v, dict):
                logging.debug(v)
            else:
                logging.debug(v.replace('\n',''))
    
    logging.debug("[INFO] Push Docker Image %s To VMware Harbor" % module_name)

    push_info = c.images.push(repository = _repository, 
                               tag = tag,
                               stream = True,
                               auth_config = {'username': 'username',
                                              'password': 'password'})
    for j in push_info:
        for k,v in eval(j).items():
            if isinstance(v, dict):
                if v == {}:continue
                logging.debug(v)
            else:
                logging.debug(v.replace('\n',''))
    logging.debug('Complete push image %s' % image_name)



def RUN(env, container_name, image_name, sleep_time=None):
    P = ContainerInfo(env, container_name)
    module_name = P.module_name()
    homed_ip = P.homed_ip()
    container_ip = P.container_ip()
    net_name = P.net_name()
    dns_server = P.dns_server()
    syslog_address = P.syslog_address()
    service_group = P.service_group()
    mq_gray_switch = P.mq_gray_switch()


    cpu2 = P.cpu2()
    binds2 = P.binds2()
    nat_port2 = P.nat_port2()
    dockerinfo=("ECS IP=%s docker_name=%s docker_ip=%s " % (homed_ip, container_name, container_ip))
    #logging.info("\nARGS  =  -d\t--restart=on-failure:5\n\t --name\t{0} \n\t -h\t{0} \
    #\n\t --network {1} \n\t --ip\t{2} {3} -P  \n\t{4} -m   {5} \n\t{6} \n\t {7}".format(
    #container_name, net_name, container_ip, nat_port2, cpu2, P.memory(), binds2, image_name))
    #docker宿主机从Harbor拉取镜像
    C = docker.DockerClient(base_url='tcp://%s:2375' % (homed_ip))
    C.images.pull(name = image_name.split(':')[0], 
                  tag  = image_name.split(':')[1])

    #生成Low-level API 配置
    L = docker.APIClient(base_url='tcp://%s:2375' % (homed_ip))
    _net_config = L.create_networking_config({
                  net_name: L.create_endpoint_config(ipv4_address = container_ip)})
    _host_config = L.create_host_config(restart_policy={"Name":"on-failure","MaximumRetryCount":50},
                                        cap_add=["SYS_PTRACE"],
                                        cpuset_cpus= P.cpu(),
                                        mem_limit = P.memory(),
                                        port_bindings= P.nat_port(),
                                        publish_all_ports=True,
                                        dns=dns_server,
                                        log_config = {"type":"syslog","config":{"syslog-address":syslog_address, 
                                                                                           "tag":container_name}},
                                        binds=P.binds())


    envi={'container_appName':module_name,
          'container_IP':container_ip,
          'LANG':'en_US.UTF-8',
          'SERVICE.GROUP':service_group,
          'MQ.GRAY.SWITCH':mq_gray_switch}

    try:
        container = L.create_container(image = image_name,
                                       hostname = container_name,
                                       name = container_name,
                                       environment = envi,
                                       stop_timeout = 60,
                                       networking_config = _net_config,
                                       host_config = _host_config)
    except (docker.errors.APIError) as error_info:
        logging.error('homed ip %s container_name %sFailed to create container,\
        \n The error message captured is%s' % ( homed_ip, container_name, error_info))
        sys.exit(1)

    logging.debug("%s starting" % dockerinfo)
    logging.debug("docker id =%s" % container.get('Id'))
    

    try:
        L.start(container=container.get('Id'))
    except (docker.errors.APIError) as error_info:
        logging.error('%s startingStartup failed,\n The error message captured is%s' % (dockerinfo, error_info))
        sys.exit(1)

    # check container health status
    if not sleep_time: sleep_time = 60
    logging.debug('Sleep for %s seconds to check the status of the container' %  sleep_time)
    time.sleep(float(sleep_time))

    h_num=13 #healthcheck_num
    for num in range(1,h_num):
        try:
            healthstatus = L.inspect_container(container_name)['State']['Health']['Status']
        except (KeyError) as error_info:
            break
        if healthstatus == "healthy":
            break
        elif healthstatus == "unhealthy":
            logging.error('%s unhealthy, stop deploying' % dockerinfo)
            sys.exit(1)
        elif healthstatus == "starting":
            logging.debug('Health check number %s is starting, sleep 30 second ' %  num)
            if num == (h_num-1):
                logging.error('The last health check failed, stop deploying')
                sys.exit(1)
            time.sleep(30)
            continue
    # Check container startup status
    status = C.containers.get(container_name).status
    if status == "running":
        logging.info("%s update success" % dockerinfo)
    else:
        logging.error("%s run failed with status %s" % (dockerinfo, status))
        sys.exit(1)



class ContainerChange(object):
    def __init__(self, env, module_name, container_list=None, tag=None, sleep=None):
        self.env = env
        self.module_name = module_name
        if tag: self.tag = tag
        else:   self.tag = datetime.datetime.now().strftime('%Y%m%d%H%M')
        self.sleep = sleep
        if container_list:
            self.mult_container_name = container_list
        else:
            self.mult_container_name = CONF[env]['module_dict2'][module_name]
        #本次容器数量
        self.cur_container_num=len(self.mult_container_name)
        #配置文件中的容器数量
        self.cnf_container_num = len(CONF[env]['module_dict2'][module_name])
        self.repository = 'h.cn/%s/%s' % (self.env, self.module_name)
        self.image_name = 'h.cn/%s/%s:%s' % (self.env, self.module_name, self.tag)

    def update(self):
        logging.info("update %s %s tag %s" % (self.env, self.module_name, self.tag))
        BUILD(self.env, self.module_name, self.tag)
        for _container_name in self.mult_container_name:
            logging.debug("update container %s %s tag %s" % (self.env, _container_name, self.tag))
            #if self.cnf_container_num >1:
            #    nginx_control(self.env, _container_name,'off')
            #    eureka_control(self.env, _container_name,'out')
            container_control(self.env, _container_name,'remove')
            RUN(self.env, _container_name, self.image_name, self.sleep)
            #if self.cnf_container_num >1:
            #    nginx_control(self.env, _container_name,'on')

    def rollback(self):
        logging.debug("rollback %s %s tag %s" % (self.env, self.module_name, self.tag))
        for _container_name in self.mult_container_name:
            container_control(self.env, _container_name,'remove')
            RUN(self.env, _container_name, self.image_name, self.sleep)

    def ui_rollback(self):
        print("Ready to roll back the module %s" % self.module_name)
        c = docker.DockerClient(base_url='unix://var/run/docker.sock')
        #删除未使用无标签的镜像
        #c.images.prune(filters={'dangling':'0'})
        image_list = c.images.list(name=self.repository)
        print("image_list=%s" % image_list)
        #取tag
        taglist = [line.tags[0].split(':')[1] for line in image_list]
        print("taglist=%s" % taglist)
        taglist.sort()
        taglist.reverse()
        adict = {str(key): value for key, value in enumerate(taglist)}
        print('%-6s %-5s' % ('index', 'tag'))
        for ind, tag in enumerate(taglist):
            print('%-6s %-5s' % (ind, tag))
        print("\nr 返回主菜单\nq Quit")
        choice = raw_input('\n请选择模块%s tag对应的index: ' % self.module_name)
        if choice == "r":home_page()
        elif choice == "q":quit_page()
        rollback_image_name = 'h.cn/%s/%s:%s' % (self.env, self.module_name, adict[choice])
        for _container_name in self.mult_container_name:
            container_control(self.env, _container_name,'remove')
            RUN(self.env, _container_name, rollback_image_name)


def container_control(env, container_name, type):
    P = ContainerInfo(env, container_name)
    homed_ip = P.homed_ip()
    container_ip = P.container_ip()
    dockerinfo=("ECS IP=%s docker_name=%s docker_ip=%s" % (homed_ip, container_name, container_ip))
    c = docker.DockerClient(base_url='tcp://%s:2375' % (homed_ip))
    rm_dict={'force':True}
# 强制杀死
    if type == 'remove':
        try:
            logging.debug("%s stop" % dockerinfo)
            c.containers.get(container_name).kill(signal=9)
        except (docker.errors.NotFound) as error_info:
            logging.info('%s does not exist, skip deletion\
            \nThe captured information is %s' % ( dockerinfo, error_info))
        except (docker.errors.APIError) as error_info:
            c.containers.get(container_name).remove(**rm_dict)
            logging.warning('%s docker.errors.APIError, skip deletion\
            \nThe captured information is %s' % (dockerinfo, error_info))
        #  如果没有异常发生，则执行这段代码
        else:
            logging.debug('%s remove' % dockerinfo)
            c.containers.get(container_name).remove(**rm_dict)

# old程序 优雅停止容器, 超过60秒超时失败, 无法捕获异常 , 上边为强制杀死
#    if type == 'remove':
#        try:
#            logging.debug("%s stop" % dockerinfo)
#            stop_dict={'timeout':30}
#            c.containers.get(container_name).stop(**stop_dict)
#            #c.containers.get(container_name).kill(signal=9)       #docker.errors.APIError
#        except (docker.errors.NotFound) as error_info:
#            logging.warning('%s container_name %s Container does not exist, skip deletion\
#            \nThe captured information is %s' % (homed_ip, container_name, error_info))
#        else:
#            logging.debug('%s remove %s old %s' % (homed_ip, container_name))
#            rm_dict={'force':True}
#            c.containers.get(container_name).remove(**rm_dict)

def nginx_control(env, container_name, type):
    P = ContainerInfo(env, container_name)
    nginx_ip = P.nginx_ip()
    container_ip = P.container_ip()
    ng_sleep = 10 if env == 'pro' else 1
    for _ip in nginx_ip:
        grep_status=subprocess.call('%s%s "%s"' % ('ssh root@', _ip, 'grep -q %s /etc/nginx/nginx.conf' % container_ip), shell=True)
        #如果没在nginx.conf找到容器ip, 跳过
        if grep_status == 1:continue
        mod_nginx_status = subprocess.call('%s%s "%s"' % ('ssh root@', _ip, '/oma/deploy/scripts/ctrl_nginx.sh %s %s' % (type, container_ip)), shell=True)
        logging.info('/oma/deploy/scripts/ctrl_nginx.sh %s %s' % (type, container_ip))
        if mod_nginx_status == 0:
            logging.debug('from nginx%-16s %sline docker_ip=%-14s sleep %s second' %(_ip, type, container_ip, ng_sleep) )
            time.sleep(ng_sleep)
        elif mod_nginx_status == 15:
            logging.info('修改%snginx.conf前有语法错误,跳过' %_ip)
        elif mod_nginx_status == 16:
            logging.info('修改%snginx.conf后有语法错误,已经回滚到修改前版本'%_ip)
        elif mod_nginx_status == 17:
            logging.info('输入的docker ip%s格式错误'%container_ip)


def eureka_control(env, container_name, type):
    P = ContainerInfo(env, container_name)
    headers={'content-type': 'application/json'}
    eu_sleep = 35 if env == 'pro' else 30

    if P.eureka_appname():
        reg_url = de_register_url = 'http://%s:%s@%s/eureka/apps/%s/%s.%s:%s:%s' % (P.eureka_user(), P.eureka_password(), P.eureka_url(), P.eureka_appname(), container_name, P.net_name(), P.module_name(), P.eureka_port() )
        out_of_service_url='%s/status?value=OUT_OF_SERVICE' % (reg_url)
        rest_o=requests.put(out_of_service_url, headers=headers)
        if rest_o.status_code != 200:
            logging.warning('from %s eureka out of service  %s failed' % (env, container_name) )
            return
        time.sleep(eu_sleep)
        rest_d=requests.delete(de_register_url, headers=headers)
        if rest_d.status_code != 200:
            logging.warning('from %s eureka delete service %s failed' % (env, container_name) )
            return




# 定义页面菜单 ------------------------------------------------------------------------------------

menu_list = {
'home_page_menu': 
"""
        --------------------------
               容器管理工具
        --------------------------
         1 开发环境         (dev)
         2 预生产环境       (pre)
         3 生产环境         (pro)
         4 测试环境1        (tst)
         5 测试环境2        (ttt)
         6 灰度环境         (gra)
         7 测试环境3        (tsm)
         8 预生产环境       (npe)
         9 扫码灰度环境     (grb)
         q Quit

         Please enter the index: """ ,

'func_menu':
"""
        --------------------------
               容器管理工具
        --------------------------
         1 升级模块
         2 回滚模块
         3 查看模块信息
         r 返回主菜单
         q Quit

         Please enter the index: """ ,

'module_list_menu':
"""
r 返回主菜单
q Quit

Please enter the index: """ ,

'help': 
"""
Usage:  dockercon [OPTION] [ENV_NAME] [module_name] [TAG]

-T --type       类型 build rollback
-e --env        环境
-m --module     模块名称
-c --container  容器名称或all  多个容器以','分隔
-t --tag        tag
-s --sleep      更新容器间隔
-u --ui         进入交互模式

示例:
dockercon -T update   -e tst -m sms -t tag

"""
}


# Defines the page function ----------------------------------------------------------------
def quit_page():
    str = '\n     Exit Docker console !'
    print(str.center(30, ' '))
    sys.exit(0)

def invalid_input_output():
    print('输入有误，请重新输入:')

#---------------------------------------------------------------------------------------------
def create_module_list(env):
    list = PrettyTable(['ModuleName', 'ContainerName', 'ContainerIP', 'HomedIP'])
    list.align['ModuleName'] = 'l'
    list.align['ContainerName'] = 'l'
    list.align['ContainerIP'] = 'l'
    list.align['HomedIP'] = 'l'
    list.padding_width = 1

    #list.add_row(['%s' % '-' * 21, '%s' % '-' * 26, '%s' % '-' * 15, '%s' % '-' * 15])
    #ipdb.set_trace()
    for ind2 in sorted(CONF[env]["container_inf"].keys()):
        c_name=ind2
        m_name=CONF[env]["container_inf"][c_name]["module_name"]
        c_ip=CONF[env]["container_inf"][c_name]["ip"]
        h_ip=CONF[env]["container_inf"][c_name]["homed_ip"]
        list.add_row([m_name, c_name, c_ip, h_ip])
    print(list)

#---------------------------------------------------------------------------------------------
def home_page():
    global ENV
    subprocess.call('clear', shell=True)
    _env = {'1':'dev', '2': 'pre', '3': 'pro', '4': 'tst', '5': 'ttt',  '6': 'gra',  '7': 'tsm', '8': 'npe', '9': 'grb'}
    while True:
        try:
            choice = raw_input(menu_list['home_page_menu']).strip()
            if choice == 'q': quit_page()
            elif choice in [m for m in _env]: break
        except (KeyboardInterrupt, EOFError):
            quit_page()

    #根据数字选择环境名称 创建全局变量
    ENV = _env[choice]
    ui_load_conf(ENV)
    select_page()

#---------------------------------------------------------------------------------------------
def select_page():
    global deploy_type
    subprocess.call('clear', shell=True)
    _deploy_type={'1':'update', '2': 'rollback', '3': 'view'}
    all_choices = {'1': module_list_menu, '2': module_list_menu,
                   '3': module_list_menu}
    try:
        choice = raw_input(menu_list['func_menu']).strip()
        if choice == 'q': quit_page()
        elif choice == 'r': home_page()
        elif choice not in [m for m in all_choices]: select_page()
    except (KeyboardInterrupt, EOFError):
        quit_page()
    deploy_type=_deploy_type[choice]
    all_choices[choice]()


def module_list_menu():
    while True:
        subprocess.call('clear', shell=True)
        str = "%s环境模块列表" % ENV
        print("\033[1;33m%s" % str.center(100,' '))
        #print(string.center('\033[1;33m%s环境模块列表' % ENV, 100))
        create_module_list(ENV)
        try:
            index = raw_input(menu_list['module_list_menu']).strip()
            print('index=%s' % index)
            if index == 'q': quit_page()
            elif index == 'r': home_page()
        except (KeyboardInterrupt, EOFError):
            quit_page()
        all_container_index= []
        for d in ["module_dict2"]:
            for i in (CONF[ENV][d].keys()):
                all_container_index.append(i)
        #print("all_container_index=%s" % all_container_index)
        if index not in all_container_index:
            print("\033[1;33m输入的index不存在, 1秒后返回, 请重新输入")
            time.sleep(1)
            continue

        if deploy_type == 'update':
            tag = time.strftime("%Y%m%d%H%M")
            p=ContainerChange(ENV, index, tag)
            p.update()
            break

        elif deploy_type == 'rollback':
            r=ContainerChange(ENV, index)
            r.ui_rollback()
            break


class Options(object):
    def __init__(self, args):
        self.args = args
        self.TYPE = None
        self.ENV = None
        self.ModuleName = None
        self.ContainerList = None
        self.SleepTime = None
        self.TAG = None

        try:
            import getopt
            options,args = getopt.getopt(args,"hT:e:m:c:t:s:u",
                ["help","type=","env=","module=","container=","tag=","sleep=","ui"])
        except getopt.error, exc:
            print("输入的参数错误,请重新输入")
            sys.exit(1)

        for opt, arg in options:
            if opt in ('-h', '--help'):
                self.help()
            elif opt in ("-T","--type"):
                self.TYPE = arg
            elif opt in ("-e","--env"):
                self.ENV = arg
            elif opt in ("-m","--module"):
                self.ModuleName = arg
            elif opt in ("-c","--container"):
                if arg == 'all':
                    self.ContainerList = None
                else:
                    self.ContainerList = arg.split(',')
            elif opt in ("-s","--sleep"):
                self.SleepTime = arg
            elif opt in ("-t","--tag"):
                self.TAG = arg
            elif opt in ("-u","--ui"):
                home_page()
            else:
                print('dockercon: option %s unknown to getopt, try dockercon -h for a list of all the options' % opt)
                sys.exit(1)

    def help(self):
        print(menu_list['help'])
        sys.exit(0)

#---------------------------------------------------------------------------------------------
def main():
    global CONF
    if op.ENV == "pro":
        CONF_FILE = "%s/%s" % (os.path.dirname(os.path.realpath(__file__)), ONLINE_CONF_NAME)
    else:
        CONF_FILE = "%s/%s" % (os.path.dirname(os.path.realpath(__file__)), OFFLINE_CONF_NAME)
    with open(CONF_FILE) as f:
        CONF = json.load(f)

    #sleep_time = None
    argv_num = len(sys.argv) - 1
    env_tuple = ('pro','pre','dev','tst','ttt','tsm','npe','gra','grb')

    if op.ENV not in env_tuple:
        print("env=%s does not exist" % op.ENV)
        sys.exit(1)
    elif op.TYPE == 'update':
        p = ContainerChange(op.ENV, op.ModuleName, op.ContainerList, op.TAG, op.SleepTime)
        p.update()
        sys.exit(0)
    elif op.TYPE == 'rollback':
        r = ContainerChange(op.ENV, op.ModuleName, op.ContainerList, op.TAG)
        r.rollback()
        sys.exit(0)


def debug_arg():
    argv_num = len(sys.argv)
    print(sys.argv)
    print("argv_num=%s" % argv_num)
    for i in range(1,argv_num-1):
        print("sys.argv[i]=%s" % sys.argv[i])
    print(type(argv_num))


if __name__ == '__main__':
    op = Options(sys.argv[1:])
    main()

