#!/usr/bin/env python2
# encoding: utf-8

# Author: Alexandre Fonseca
# Description:
#   Installs, configures and manages Hadoop on a set of nodes
#   in a cluster.
# Associated guide:
#   http://www.alexjf.net/blog/distributed-systems/hadoop-yarn-installation-definitive-guide

import os
from fabric.api import run, cd, env, settings, put, sudo
from fabric.context_managers import shell_env

###############################################################
#  START OF YOUR CONFIGURATION (CHANGE FROM HERE, IF NEEDED)  #
###############################################################
IS_CONNECTED = False
HADOOP_VERSION = "2.5.0"
HADOOP_PACKAGE = "hadoop-%s" % HADOOP_VERSION
HADOOP_PACKAGE_FILE = HADOOP_PACKAGE + ".tar.gz"
HADOOP_PACKAGE_URL = "http://apache.mirror.digionline.de/hadoop/common/%s/%s.tar.gz" % (HADOOP_PACKAGE, HADOOP_PACKAGE)
HADOOP_PREFIX = "/home/hduser/%s" % HADOOP_PACKAGE
HADOOP_CONF = os.path.join(HADOOP_PREFIX, "etc/hadoop")

SPARK_VERSION = "1.0.2"
SPARK_PACKAGE = "spark-%s" % SPARK_VERSION
SPARK_PACKAGE_FILE = SPARK_PACKAGE + "-bin-hadoop2.tgz"
#SPARK_ADDR =        "http://ftp.halifax.rwth-aachen.de/apache/spark/spark-0.9.1/spark-0.9.1-bin-hadoop2.tgz"
SPARK_PACKAGE_URL = "http://ftp.halifax.rwth-aachen.de/apache/spark/%s/%s-bin-hadoop2.tgz" % (SPARK_PACKAGE, SPARK_PACKAGE)
SPARK_PREFIX = "/home/hduser/%s" % SPARK_PACKAGE


# Change this to the command you would use to install packages on the
# remote hosts.
#PACKAGE_MANAGER_INSTALL = "apt-get install %s" # Debian/Ubuntu
#PACKAGE_MANAGER_INSTALL = "pacman -S %s" # Arch Linux
#PACKAGE_MANAGER_INSTALL = "yum install %s" # CentOS
PACKAGE_MANAGER_INSTALL = "zypper install %s" # OpenSuse
 
# Change this list to the list of packages required by Hadoop
# In principle, should just be a JRE for Hadoop, Python
# for the Hadoop Configuration replacement script and wget
# to get the Hadoop package
REQUIREMENTS = [] #current suse install
#REQUIREMENTS = ["wget", "python", "openjdk-7-jdk"] # Debian/Ubuntu
#REQUIREMENTS = ["wget", "python", "jre7-openjdk-headless"] # Arch Linux
#REQUIREMENTS = ["wget", "python", "java-1.7.0-openjdk-devel"] # CentOS

#JAVA_HOME = "/usr/lib/jvm/java-7-openjdk-amd64"
JAVA_HOME = "/usr/lib64/jvm/java"

ENVIRONMENT_FILE = "/home/hduser/.bashrc"
ENVIRONMENT_VARIABLES = [
                         ("JAVA_HOME", JAVA_HOME), # Debian/Ubuntu 64 bits not - works for OpenSuse now
                         #("JAVA_HOME", "/usr/lib/jvm/java-7-openjdk"), # Arch Linux
                         #("JAVA_HOME", "/usr/lib/jvm/java"), # CentOS
                         ("HADOOP_PREFIX", HADOOP_PREFIX),
                         ("HADOOP_HOME", HADOOP_PREFIX),
                         ("HADOOP_COMMON_HOME", HADOOP_PREFIX),
                         ("HADOOP_CONF_DIR",HADOOP_PREFIX+"/etc/hadoop"),
                         ("HADOOP_HDFS_HOME", HADOOP_PREFIX),
                         ("HADOOP_MAPRED_HOME", HADOOP_PREFIX),
                         ("HADOOP_YARN_HOME", HADOOP_PREFIX),
                         ("SPARK_HOME", SPARK_PREFIX)
                         ]

NET_INTERFACE="eth0"
SSH_USER = "hduser"

NAMENODE_HOST = "master"
RESOURCEMANAGER_HOST = "master"
SLAVE_HOSTS = ["threesome","squirting","romantic","rimming","orgy","milf","masturbation","lingerie","lesbian","interracial","hentai","hairy","gangbang","fisting","fetish","facials","doublepenetration","cumshot","creampie"]
#NAMENODE_HOST = "namenode.alexjf.net"
#RESOURCEMANAGER_HOST = "resourcemanager.alexjf.net"
#SLAVE_HOSTS = ["slave%d.alexjf.net" % i for i in range(1, 6)]
# Or equivalently
#SLAVE_HOSTS = ["slave1.alexjf.net", "slave2.alexjf.net",
#          "slave3.alexjf.net", "slave4.alexjf.net",
#          "slave5.alexjf.net"]

# If you'll be running map reduce jobs, you should choose a host to be
# the job tracker
JOBTRACKER_HOST = "master"
JOBTRACKER_PORT = 8021

# If you'll run MapReduce jobs, you might want to set a JobHistory server.
# e.g: JOBHISTORY_HOST = "jobhistory.alexjf.net"
JOBHISTORY_HOST = "master"
JOBHISTORY_PORT = 10020

CORE_SITE_VALUES = {
    "fs.defaultFS": "hdfs://%s/" % NAMENODE_HOST,
}

HDFS_SITE_VALUES = {
    "dfs.datanode.data.dir": "file://%s/hdfs/datanode" % HADOOP_PREFIX,
    "dfs.namenode.name.dir": "file://%s/hdfs/namenode" % HADOOP_PREFIX,
}

YARN_SITE_VALUES = {
    "yarn.resourcemanager.hostname": RESOURCEMANAGER_HOST,
    "yarn.scheduler.minimum-allocation-mb": 2048,
    "yarn.scheduler.maximum-allocation-mb": 8192,
    "yarn.scheduler.minimum-allocation-vcores": 1,
    "yarn.scheduler.maximum-allocation-vcores": 8,
    "yarn.nodemanager.resource.memory-mb": 8192,
    "yarn.nodemanager.resource.cpu-vcores": 8,
    "yarn.log-aggregation-enable": "true",
    "yarn.nodemanager.aux-services": "mapreduce_shuffle",
}

MAPRED_SITE_VALUES = {
    "yarn.app.mapreduce.am.resource.mb": 4096,
    "yarn.app.mapreduce.am.command-opts": "-Xmx3280m",
    "mapreduce.framework.name": "yarn",
    "mapreduce.map.cpu.vcores": 1,
    "mapreduce.map.memory.mb": 2048,
    "mapreduce.map.java.opts": "-Xmx1640m",
    "mapreduce.reduce.cpu.vcores": 1,
    "mapreduce.reduce.memory.mb": 4096,
    "mapreduce.reduce.java.opts": "-Xmx3280m",
}

##############################################################
#  END OF YOUR CONFIGURATION (CHANGE UNTIL HERE, IF NEEDED)  #
##############################################################

#####################################################################
#  DON'T CHANGE ANYTHING BELOW (UNLESS YOU KNOW WHAT YOU'RE DOING)  #
#####################################################################
env.user = SSH_USER
hosts = [NAMENODE_HOST, RESOURCEMANAGER_HOST, JOBHISTORY_HOST] + SLAVE_HOSTS
seen = set()
# Remove empty hosts and duplicates
cleanedHosts = [host for host in hosts if host and host not in seen and not seen.add(host)]
env.hosts = cleanedHosts

if JOBTRACKER_HOST:
    MAPRED_SITE_VALUES["mapreduce.jobtracker.address"] = "%s:%s" % \
        (JOBTRACKER_HOST, JOBTRACKER_PORT)

if JOBHISTORY_HOST:
    MAPRED_SITE_VALUES["mapreduce.jobhistory.address"] = "%s:%s" % \
        (JOBHISTORY_HOST, JOBHISTORY_PORT)

# FUNCTION TO RUN WITH JAVA ENVIRONMENT VARIABLE SET PROPERLY

def jrun(command):
    with shell_env(JAVA_HOME=JAVA_HOME):
        run(command)

# MAIN FUNCTIONS
def all():
    installDependencies()
    install()
    config()
    setupEnvironment()
    formatHdfs()
    writeSlaves()
    installSpark()

def install_all():
    installDependencies()
    install()
    installSpark()
    setupEnvironment()
    writeSlaves()

def writeSlaves():
    slaves_file = HADOOP_PREFIX + "/etc/hadoop/slaves"
    run("> %s" % slaves_file)
    for slave in SLAVE_HOSTS:
   	run( 'echo %s >> %s' % (slave, slaves_file) ) 

def installDependencies():
    for requirement in REQUIREMENTS:
        sudo(PACKAGE_MANAGER_INSTALL % requirement)

def installSpark():
    install(SPARK_PREFIX, SPARK_PACKAGE_FILE, SPARK_PACKAGE_URL)
    run("ln -f -s %s %s" % (SPARK_PREFIX, "~/spark"))

def install(prefix=HADOOP_PREFIX, package=HADOOP_PACKAGE_FILE, package_url=HADOOP_PACKAGE_URL):
    installDirectory = os.path.dirname(prefix)
    run("mkdir -p %s" % installDirectory)
    with cd(installDirectory):
        with settings(warn_only=True):
            if run("test -f %s" % package).failed:
                get(package, package_url)
        run("tar --overwrite -xf %s" % package)
    run("ln -f -s %s %s" % (HADOOP_PREFIX, "~/hadoop"))

def config():
    changeHadoopProperties("core-site.xml", CORE_SITE_VALUES)
    changeHadoopProperties("hdfs-site.xml", HDFS_SITE_VALUES)
    changeHadoopProperties("yarn-site.xml", YARN_SITE_VALUES)
    changeHadoopProperties("mapred-site.xml", MAPRED_SITE_VALUES)

def configRevertPrevious():
    revertHadoopPropertiesChange("core-site.xml")
    revertHadoopPropertiesChange("hdfs-site.xml")
    revertHadoopPropertiesChange("yarn-site.xml")
    revertHadoopPropertiesChange("mapred-site.xml")

def setupEnvironment():
    for var, value in ENVIRONMENT_VARIABLES:
        setEnvironmentVariable(var, value)

def formatHdfs():
    if env.host == NAMENODE_HOST:
        cmd = "%s/bin/hdfs namenode -format" % HADOOP_PREFIX
        jrun(cmd)

def get(package, package_url):
    if IS_CONNECTED:
    #if env.host == NAMENODE_HOST:
        run("wget -O %s %s" % (package, package_url))
        run("cp %s /srv/files/packages/%s" % (package,package))
    else:
        run("cp /srv/files/packages/%s %s" % (package, package))
        
        
       

def setupSelfReferences():
    privateIp = run("ifconfig %s | grep 'inet\s\+' | awk '{print $2}' | cut -d':' -f2" % NET_INTERFACE).strip()
    sudo("echo '" + privateIp + " " + env.host + "' >> /etc/hosts")

def start():
    operationOnHadoopDaemons("start")

def stop():
    operationOnHadoopDaemons("stop")

def test():
    if env.host == RESOURCEMANAGER_HOST:
        jrun("%(prefix)/bin/hadoop jar %(prefix)/share/hadoop/yarn/hadoop-yarn-applications-distributedshell-%(version)s.jar org.apache.hadoop.yarn.applications.distributedshell.Client --jar %(prefix)/share/hadoop/yarn/hadoop-yarn-applications-distributedshell-%(version)s.jar --shell_command date --num_containers %(numContainers)d --master_memory 1024" %
             {"prefix": HADOOP_PREFIX, "version": HADOOP_VERSION, "numContainers": len(cleanedHosts)})

def testMapReduce():
    if env.host == RESOURCEMANAGER_HOST:
        jrun("%(prefix)/bin/hadoop jar %(prefix)/share/hadoop/mapreduce/hadoop-mapreduce-examples-%(version).jar randomwriter out" % {"prefix": HADOOP_PREFIX, "version": HADOOP_VERSION})

# HELPER FUNCTIONS
def getLastHadoopPropertiesBackupNumber(fileName):
    latestBak = run("ls -1 | grep %s.bak | tail -n 1" % fileName)
    latestBakNumber = -1
    if latestBak:
        latestBakNumber = int(latestBak[len(fileName) + 4:])
    return latestBakNumber

def changeHadoopProperties(fileName, propertyDict):
    if not fileName or not propertyDict:
        return
    
    with cd(HADOOP_CONF):
        with settings(warn_only=True):
            import hashlib
            replaceHadoopPropertyHash = \
                hashlib.md5(
                            open("replaceHadoopProperty.py", 'rb').read()
                            ).hexdigest()
            if run("test %s = `md5sum replaceHadoopProperty.py | cut -d ' ' -f 1`"
                   % replaceHadoopPropertyHash).failed:
                put("replaceHadoopProperty.py", HADOOP_CONF + "/")
                run("chmod +x replaceHadoopProperty.py")
        currentBakNumber = getLastHadoopPropertiesBackupNumber(fileName) + 1
        run("touch '%(file)s' && cp '%(file)s' '%(file)s.bak%(bakNumber)d'" %
            {"file": fileName, "bakNumber": currentBakNumber})
        command = "./replaceHadoopProperty.py '%s' %s" % (fileName,
                                                              " ".join(["%s %s" % (str(key), str(value)) for key, value in propertyDict.items()]))
        run(command)

def revertHadoopPropertiesChange(fileName):
    with cd(HADOOP_CONF):
        latestBakNumber = getLastHadoopPropertiesBackupNumber(fileName)
        
        # We have already reverted all backups
        if latestBakNumber == -1:
            return
        # Otherwise, perform reversion
        else:
            run("mv %(file)s.bak%(bakNumber)d %(file)s" %
                {"file": fileName, "bakNumber": latestBakNumber})

def setEnvironmentVariable(variable, value):
    with settings(warn_only=True):
        if run("test -f %s" % ENVIRONMENT_FILE).failed:
            run("touch %s" % ENVIRONMENT_FILE)
        else:
            run("cp %(file)s %(file)s.bak" % {"file": ENVIRONMENT_FILE})
    lineNumber = run("grep -n 'export\s\+%(var)s\=' '%(file)s' | cut -d : -f 1"
                     % {"var": variable, "file": ENVIRONMENT_FILE})
    try:
        lineNumber = int(lineNumber)
        run("sed -i \"" + str(lineNumber) + "s@.*@export %(var)s\=%(val)s@\" '%(file)s'" %
            {"var": variable, "val": value, "file": ENVIRONMENT_FILE})
    except ValueError:
        run("echo \"export %(var)s=%(val)s\" >> \"%(file)s\"" %
            {"var": variable, "val": value, "file": ENVIRONMENT_FILE})

def operationOnHadoopDaemons(operation):
    with cd(HADOOP_PREFIX):
        # Start/Stop NameNode
        if (env.host == NAMENODE_HOST):
            jrun("sbin/hadoop-daemon.sh %s namenode" % operation)
        
        # Start/Stop DataNode on all slave hosts
        if env.host in SLAVE_HOSTS:
            jrun("sbin/hadoop-daemon.sh %s datanode" % operation)
        
        # Start/Stop ResourceManager
        if (env.host == RESOURCEMANAGER_HOST):
            jrun("sbin/yarn-daemon.sh %s resourcemanager" % operation)
        
        # Start/Stop NodeManager on all container hosts
        if env.host in SLAVE_HOSTS:
            jrun("sbin/yarn-daemon.sh %s nodemanager" % operation)
        
        # Start/Stop JobHistory daemon
        if (env.host == JOBHISTORY_HOST):
            jrun("sbin/mr-jobhistory-daemon.sh %s historyserver" % operation)
    jrun("jps")
