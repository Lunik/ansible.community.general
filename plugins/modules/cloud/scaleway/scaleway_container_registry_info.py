#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Scaleway Serverless container registry info module
#
# Copyright (c) 2022, Guillaume MARTINEZ <lunik@tiwabbit.fr>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: scaleway_container_registry_info
short_description: Scaleway Container registry info module
author: Guillaume MARTINEZ (@Lunik)
description:
  - This module return info on container registry on Scaleway account
    U(https://developer.scaleway.com)
extends_documentation_fragment:
  - community.general.scaleway


options:
  project_id:
    type: str
    description:
      - Project identifier.
    required: true

  region:
    type: str
    description:
      - Scaleway region to use (for example fr-par).
    required: true
    choices:
      - fr-par
      - nl-ams
      - pl-waw

  name:
    type: str
    description:
      - Name of the container registry.
    required: true
'''

EXAMPLES = '''
- name: Get a container registry info
  community.general.scaleway_container_registry_info:
    project_id: '{{ scw_project }}'
    region: fr-par
    name: my-awesome-container-registry
  register: container_registry_info_task
'''

RETURN = '''
data:
    description: This is always present
    returned: always
    type: dict
    sample: {
      "container_registry": {
        "created_at": "2022-10-14T09:51:07.949716Z",
        "description": "Managed by Ansible",
        "endpoint": "rg.fr-par.scw.cloud/my-awesome-registry",
        "id": "0d7d5270-7864-49c2-920b-9fd6731f3589",
        "image_count": 0,
        "is_public": false,
        "name": "my-awesome-registry",
        "organization_id": "10697b59-5c34-4d24-8d15-9ff2d3b89f58",
        "project_id": "3da4f0b2-06be-4773-8ec4-5dfa435381be",
        "region": "fr-par",
        "size": 0,
        "status": "ready",
        "status_message": "",
        "updated_at": "2022-10-14T09:51:07.949716Z"
      }
    }
'''

from ansible_collections.community.general.plugins.module_utils.scaleway import (
    SCALEWAY_ENDPOINT, SCALEWAY_REGIONS, scaleway_argument_spec, Scaleway,
    filter_sensitive_attributes
)
from ansible.module_utils.basic import AnsibleModule

SENSITIVE_ATTRIBUTES = (
    "secret_environment_variables"
)


def info_strategy(api, wished_cn):
    response = api.get(path=api.api_path)
    if not response.ok:
        api.module.fail_json(msg='Error getting container registries [{0}: {1}]'.format(
            response.status_code, response.json['message']))

    cn_list = response.json["namespaces"]
    cn_lookup = dict((fn["name"], fn)
                     for fn in cn_list)

    if wished_cn["name"] not in cn_lookup.keys():
        msg = "Error during container registries lookup: Unable to find container registry named '%s' in project '%s'" % (wished_cn["name"],
                                                                                                                          wished_cn["project_id"])

        api.module.fail_json(msg=msg)

    target_cn = cn_lookup[wished_cn["name"]]

    response = api.get(path=api.api_path + "/%s" % target_cn["id"])
    if not response.ok:
        msg = "Error during container registry lookup: %s: '%s' (%s)" % (response.info['msg'],
                                                                         response.json['message'],
                                                                         response.json)
        api.module.fail_json(msg=msg)

    return response.json


def core(module):
    region = module.params["region"]
    wished_container_namespace = {
        "project_id": module.params["project_id"],
        "name": module.params["name"]
    }

    api = Scaleway(module=module)
    api.api_path = "registry/v1/regions/%s/namespaces" % region

    summary = info_strategy(api=api, wished_cn=wished_container_namespace)

    module.exit_json(changed=False, container_registry=filter_sensitive_attributes(summary, SENSITIVE_ATTRIBUTES))


def main():
    argument_spec = scaleway_argument_spec()
    argument_spec.update(dict(
        project_id=dict(type='str', required=True),
        region=dict(type='str', required=True, choices=SCALEWAY_REGIONS),
        name=dict(type='str', required=True)
    ))
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    core(module)


if __name__ == '__main__':
    main()
