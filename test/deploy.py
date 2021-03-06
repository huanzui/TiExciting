# -*- coding: utf-8 -*-

import sys

sys.path.append('..')

# from ansible_util.ansible_task import AnsibleTask

TIDB_VERSION = 'v3.0.3'
TIDB_URL = 'http://download.pingcap.org/tidb-%s-linux-amd64.tar.gz' % TIDB_VERSION
TIDB_SHA256_URL = 'http://download.pingcap.org/tidb-%s-linux-amd64.sha256' % TIDB_VERSION
TIDB_DIR_NAME = 'tidb-%s-linux-amd64' % TIDB_VERSION


def gen_comm_script(template, uid, data_dir, server_ip, server_port, status_port, pd_cluster):
    pd_cluster = ','.join(
        [('%s:%d' if len(server) == 2 else '%s=http://%s:%d') % server for server in pd_cluster])
    template = template.replace('<uid>', uid)
    template = template.replace('<data_dir>', data_dir)
    template = template.replace('<server_ip>', server_ip)
    template = template.replace('<server_port>', str(server_port))
    template = template.replace('<status_port>', str(status_port))
    template = template.replace('<pd_cluster>', pd_cluster)
    return template


def gen_pd_script(uid, data_dir, server_ip, server_port, status_port, pd_cluster):
    with open('../shell/launch-pd.template', 'r') as f:
        template = f.read()
    return gen_comm_script(template, uid, data_dir, server_ip, server_port, status_port, pd_cluster)


def gen_tidb_script(uid, data_dir, server_ip, server_port, status_port, pd_cluster):
    with open('../shell/launch-tidb.template', 'r') as f:
        template = f.read()
    return gen_comm_script(template, uid, data_dir, server_ip, server_port, status_port, pd_cluster)


def gen_tikv_script(uid, data_dir, server_ip, server_port, status_port, pd_cluster):
    with open('../shell/launch-tikv.template', 'r') as f:
        template = f.read()
    return gen_comm_script(template, uid, data_dir, server_ip, server_port, status_port, pd_cluster)


def write_to_file(path, content):
    with open(path, 'w') as f:
        f.write(content)


'''
{
  "dir": "xxx",
  "status_port": 123,
  "server_port": 456,
  "pd_cluster_ip_uid": {"ip_port": "uid1"},
  "uid": "ip:uid"
}
'''


def deploy(config):
    # 1. 下载sha256
    task = AnsibleTask('get_url', 'url=%s dest=/tmp/tidb.sha256 force=yes' % TIDB_SHA256_URL)
    print(task.get_result())

    # 2. 取出sha256
    task = AnsibleTask('shell', "cat /tmp/tidb.sha256|awk '{print $1}'")
    result = task.get_result()
    print(result)
    sha256 = result['success']['localhost']['stdout']

    task = AnsibleTask('stat', 'checksum_algorithm=sha256 path=/tmp/tidb.tar.gz')
    result = task.get_result()
    print(result)
    stat = result['success']['localhost']['stat']
    if not stat['exists'] or stat['checksum'] != sha256:
        # 3. 下载大礼包并检查sha256
        task = AnsibleTask('get_url', 'url=%s dest=/tmp/tidb.tar.gz force=yes checksum=sha256:%s' % (TIDB_URL, sha256))
        print(task.get_result())

    # 4. 解压大礼包
    task = AnsibleTask('shell', 'tar -xzf /tmp/tidb.tar.gz')
    print(task.get_result())

    # 5. 分发大礼包
    # pd   => /tmp/{{TIDB_DIR_NAME}}/bin/pd-server
    # tikv => /tmp/{{TIDB_DIR_NAME}}/bin/tikv-server
    # tidb => /tmp/{{TIDB_DIR_NAME}}/bin/tidb-server
    pd_path = '/tmp/%s/bin/pd-server' % TIDB_DIR_NAME
    tikv_path = '/tmp/%s/bin/tikv-server' % TIDB_DIR_NAME
    tidb_path = '/tmp/%s/bin/tidb-server' % TIDB_DIR_NAME

    task = AnsibleTask('copy', 'src=%s dest=~/TiExciting/pd/ mode=0755' % pd_path, 'pd_servers')
    print(task.get_result())

    task = AnsibleTask('copy', 'src=%s dest=~/TiExciting/tikv/ mode=0755' % tikv_path, 'tikv_servers')
    print(task.get_result())

    task = AnsibleTask('copy', 'src=%s dest=~/TiExciting/tidb/ mode=0755' % tidb_path, 'tidb_servers')
    print(task.get_result())

    # 6. 生成执行脚本

    # pd-servers
    write_to_file('/tmp/launch.sh', gen_pd_script('pd_xiaohou', '/home/tidb/data1', '192.168.233.128', 2380, 2379,
                                                  [('pd_xiaohou', '192.168.233.128', 2380)]))
    task = AnsibleTask('copy', 'src=/tmp/launch.sh dest=/home/tidb/TiExciting/pd/ mode=0755', '192.168.233.128')
    print(task.get_result())

    # tikv-servers
    for server_ip in ['192.168.233.129', '192.168.233.130', '192.168.233.131']:
        write_to_file('/tmp/launch.sh', gen_tikv_script('pd_xiaohou', '/home/tidb/data1', server_ip, 20160, 20180,
                                                        [('192.168.233.128', 2380)]))
        task = AnsibleTask('copy', 'src=/tmp/launch.sh dest=/home/tidb/TiExciting/tikv/ mode=0755', server_ip)
        print(task.get_result())

    # tidb-servers
    write_to_file('/tmp/launch.sh', gen_tidb_script('pd_xiaohou', '/home/tidb/data2', '192.168.233.128', 4000, 10080,
                                                    [('192.168.233.128', 2380)]))
    task = AnsibleTask('copy', 'src=/tmp/launch.sh dest=/home/tidb/TiExciting/tidb/ mode=0755', '192.168.233.128')
    print(task.get_result())

    # 7. 启动
    task = AnsibleTask('shell', 'bash /home/tidb/TiExciting/pd/launch.sh', 'pd_servers', True)
    print(task.get_result())

    task = AnsibleTask('shell', 'bash /home/tidb/TiExciting/tikv/launch.sh', 'tikv_servers', True)
    print(task.get_result())

    task = AnsibleTask('shell', 'bash /home/tidb/TiExciting/tidb/launch.sh', 'tidb_servers', True)
    print(task.get_result())


if __name__ == '__main__':
    deploy(None)
    # print(gen_pd_script('pd_xiaohou', '~/data1', '192.168.233.128', 2380, 2379,
    #                     [('pd_xiaohou', '192.168.233.128', 2380), ('pd_xiaohou', '192.168.233.129', 2380)]))
    # print(gen_tidb_script('pd_xiaohou', '~/data1', '192.168.233.128', 4000, 10080,
    #                       [('192.168.233.128', 2380), ('192.168.233.129', 2380)]))
    # print(gen_tikv_script('pd_xiaohou', '~/data1', '192.168.233.129', 20160, 20180,
    #                       [('192.168.233.128', 2380), ('192.168.233.129', 2380)]))

'''

in =>
[{
"uid": "pd_xiaohu",
"role": "pd",
"server_id": "192.168.1.10",
"server_port": 8009,
"status_port": 8010,
"data_dir": "/home/tidb",
}, {
"uid": "pd_xiaohu",
"role": "tidb",
"server_id": "192.168.1.10",
"server_port": 8009,
"status_port": 8010,
"data_dir": "/home/tidb",
}]

out =>
{
  "task_id": 1,
  "config": [{}, {}],
  "status": "finished/unfinished/running",
  "hosts": {
    "pd_servers": [],
    "tikv_servers": [],
    "tidb_servers": []
  },
  "steps": [{
    "step_id": 1
    "module": "xxx",
    "arg": "xxx",
    "group": "xxx",
    "background": False,
    "extra": xxx
    "deps": [1, 2, 3],
    "status": "finished/unfinished/running"
  }]
}
'''
