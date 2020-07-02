#/bin/bash
ip_regex='^([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.([0-9]{1,2}|1[0-9][0-9]|2[0-4][0-9]|25[0-5])$'
nginx_conf="/etc/nginx/nginx.conf"
baknginx="/tmp/nginx`date '+%Y%m%d%H%M%S'`.conf"

kill_vi () {
    ps aux|grep -v grep|grep nginx.conf |grep -q vi
    if [[ $? == 0 ]];then
        ps aux|grep -v grep|grep nginx.conf |grep vi|awk '{print $2}'|xargs kill
        rm -f /etc/nginx/.nginx.conf.swp
    fi
}

if [[ $2 =~ $ip_regex ]];then
    nginx -t 2> /dev/null
    if [[ $? != 0 ]];then
        exit 15
    fi
    kill_vi
    grep -q $2  $nginx_conf
    [[ $? != 0 ]]  &&  exit 0

    \cp -a $nginx_conf $baknginx
    if [[ $1 == 'off' ]];then
        sed -i -e "/Tcp_Start/,/Tcp_End/s/^.*server $2/        #server $2/" \
               -e "/Http_Start/,/Http_End/s/^.*server $2/        #server $2/"  $nginx_conf
    elif [[ $1 == 'on' ]];then
        sed -i -e "/Tcp_Start/,/Tcp_End/s/^.*server $2/        server $2/" \
               -e "/Http_Start/,/Http_End/s/^.*server $2/        server $2/"   $nginx_conf
    fi

    #roll back nginx config
    nginx -t 2> /dev/null
    if [[ $? != 0 ]];then
        \cp -a $baknginx /etc/nginx/nginx.conf
        exit 16
    else
        systemctl reload nginx
    fi
else
    echo "ip [$2] format error"
    exit 17
fi
