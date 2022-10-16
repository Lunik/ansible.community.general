#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Scaleway Serverless function namespace info module
#
# Copyright (c) 2022, Guillaume MARTINEZ <lunik@tiwabbit.fr>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: scaleway_function_namespace_info
short_description: Scaleway Container namespace info module
author: Guillaume MARTINEZ (@Lunik)
description:
  - This module return info on function namespace on Scaleway account
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
      - Name of the function namespace.
    required: true
'''

EXAMPLES = '''
- name: Get a function namespace info
  community.general.scaleway_function_namespace_info:
    project_id: '{{ scw_project }}'
    region: fr-par
    name: my-awesome-function-namespace
  register: function_namespace_info_task
'''

RETURN = '''
data:
    description: This is always present
    returned: always
    type: dict
    sample: {
      "function_namespace": {
         "description": "",
         "environment_variables": {
             "MY_VAR": "my_value"
         },
         "error_message": null,
         "id": "531a1fd7-98d2-4a74-ad77-d398324304b8",
         "name": "my-awesome-function-namespace",
         "organization_id": "e04e3bdc-015c-4514-afde-9389e9be24b0",
         "project_id": "d44cea58-dcb7-4c95-bff1-1105acb60a98",
         "region": "fr-par",
         "registry_endpoint": "",
         "registry_namespace_id": "",
         "secret_environment_variables": "SENSITIVE_VALUE",
         "status": "pending"
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


def info_strategy(api, wished_fn):
    response = api.get(path=api.api_path)
    if not response.ok:
        api.module.fail_json(msg='Error getting function namespaces [{0}: {1}]'.format(
            response.status_code, response.json['message']))

    fn_list = response.json["namespaces"]
    fn_lookup = dict((fn["name"], fn)
                     for fn in fn_list)

    if wished_fn["name"] not in fn_lookup.keys():
        msg = "Error during function namespace lookup: Unable to find function namespace named '%s' in project '%s'" % (wished_fn["name"],
                                                                                                                        wished_fn["project_id"])

        api.module.fail_json(msg=msg)

    target_fn = fn_lookup[wished_fn["name"]]

    response = api.get(path=api.api_path + "/%s" % target_fn["id"])
    if not response.ok:
        msg = "Error during function namespace lookup: %s: '%s' (%s)" % (response.info['msg'],
                                                                         response.json['message'],
                                                                         response.json)
        api.module.fail_json(msg=msg)

    return response.json


def core(module):
    region = module.params["region"]
    wished_function_namespace = {
        "project_id": module.params["project_id"],
        "name": module.params["name"]
    }

    api = Scaleway(module=module)
    api.api_path = "functions/v1beta1/regions/%s/namespaces" % region

    summary = info_strategy(api=api, wished_fn=wished_function_namespace)

    module.exit_json(changed=False, function_namespace=filter_sensitive_attributes(summary, SENSITIVE_ATTRIBUTES))


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
