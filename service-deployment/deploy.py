#!/usr/bin/env python

# Copyright (c) Microsoft Corporation
# All rights reserved.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
# to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import yaml
import os
import sys
import subprocess
import jinja2
import argparse



def write_generated_file(file_path, content_data):

    with open(file_path, "w+") as fout:
        fout.write(content_data)



def load_yaml_config(config_path):

    with open(config_path, "r") as f:
        cluster_data = yaml.load(f)

    return cluster_data



def read_template(template_path):

    with open(template_path, "r") as f:
        template_data = f.read()

    return template_data



def generate_from_template(template_data, cluster_config):

    generated_file = jinja2.Template(template_data).render(
        {
            "clusterinfo": cluster_config['clusterinfo'],
            "machineinfo": cluster_config["machineinfo"],
            "machinelist": cluster_config["machinelist"]
        }
    )

    return generated_file



def execute_shell_with_output(shell_cmd, error_msg):

    try:
        res = subprocess.check_output( shell_cmd, shell=True )

    except subprocess.CalledProcessError:
        print error_msg
        sys.exit(1)

    return res



def execute_shell(shell_cmd, error_msg):

    try:
        subprocess.check_call( shell_cmd, shell=True )

    except subprocess.CalledProcessError:
        print error_msg
        sys.exit(1)



def login_docker_registry(docker_registry, docker_username, docker_password):

    shell_cmd = "docker login -u {0} -p {1} {2}".format(docker_username, docker_password, docker_registry)
    error_msg = "docker registry login error"
    execute_shell(shell_cmd, error_msg)
    print "docker registry login successfully"



def generate_secret_base64code(docker_info):

    domain = docker_info[ "docker_registry_domain" ]
    username = docker_info[ "docker_username" ]
    passwd = docker_info[ "docker_password" ]

    if domain == "public":
        domain = ""

    login_docker_registry( domain, username, passwd )

    base64code = execute_shell_with_output(
        "cat ~/.docker/config.json | base64",
        "Failed to base64 the docker's config.json"
    )

    docker_info["base64code"] = base64code.replace("\n", "")



def generate_image_url_prefix(docker_info):

    domain = docker_info["docker_registry_domain"]
    namespace = docker_info["docker_namespace"]

    if domain != "public":
        prefix = "{0}/{1}/".format(domain, namespace)
    else:
        prefix = "{0}/".format(namespace)

    docker_info["prefix"] = prefix



def clean_up_generated_file(service_config):
    service_list = service_config['servicelist']

    for serv in service_list:

        template_list = service_list[serv]['templatelist']
        if 'None' in template_list:
            continue

        for template in template_list:

            if os.path.exists(template):
                shell_cmd = "rm -rf bootstrap/{0}/{1}".format(serv,template)
                error_msg = "failed to rm bootstrap/{0}/{1}".format(serv,template)
                execute_shell(shell_cmd, error_msg)

    print "Successfully clean up the generated file"



def generate_template_file(cluster_config, service_config):

    service_list = service_config['servicelist']

    for serv in service_list:

        template_list = service_list[serv]['templatelist']
        if 'None' in template_list:
            continue

        for template in template_list:

            template_data = read_template("bootstrap/{0}/{1}.template".format(serv, template))
            generate_data = generate_from_template(template_data, cluster_config)
            write_generated_file("bootstrap/{0}/{1}".format(serv, template), generate_data)



def dependency_bootstrap(serv, service_config, started_service):

    if serv == 'None':
        return
    if serv in started_service:
        return

    for pre_serv in service_config['servicelist'][serv]['prerequisite']:
        dependency_bootstrap(pre_serv, service_config, started_service)

    shell_cmd = './bootstrap/{0}/{1}'.format(serv, service_config['servicelist'][serv]['startscript'])
    error_msg = 'Failed start the service {0}'.format(serv)

    execute_shell(shell_cmd, error_msg)

    started_service[serv] = True



def bootstrap_service(service_config):

    started_service = {}

    for serv in service_config['servicelist']:

        dependency_bootstrap(serv, service_config, started_service)



def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-p', '--path', required=True, help="cluster configuration's path")
    parser.add_argument('-c', '--clean', action="store_true", help="clean the generated script")

    args = parser.parse_args()

    # step 1: load configuration from yaml file.
    config_path = args.path

    cluster_config = load_yaml_config(config_path)
    service_config = load_yaml_config("service.yaml")

    # step 2: generate base64code for secret.yaml
    generate_secret_base64code(cluster_config[ "clusterinfo" ][ "dockerregistryinfo" ])

    # step 3: generate image url prefix for yaml file.
    generate_image_url_prefix(cluster_config[ "clusterinfo" ][ "dockerregistryinfo" ])

    # step 4: generate templatefile
    generate_template_file(cluster_config, service_config)

    # step 5: Bootstrap service.
    #bootstrap_service(service_config)

    # Option : clean all the generated file.
    if args.clean:
        clean_up_generated_file(service_config)



if __name__ == "__main__":
    main()