from __future__ import annotations

import os
import time
from pathlib import Path
from pprint import pprint
from typing import Dict

import yaml
from kubernetes import client, config

from compiler import graph_base_dir
from compiler.graph.backend.utils import copy_remote_host, execute_local, kapply
from compiler.graph.ir import GraphIR
from compiler.graph.logger import BACKEND_LOG

attach_yml = """apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: {metadata_name}
spec:
  workloadSelector:
    labels:
      app: {service}
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: {bound}
      listener:
        portNumber: {port}
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.wasm
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm
          config:
            name: {name}
            root_id: {name}
            vm_config:
              vm_id: {vmid}
              runtime: envoy.wasm.runtime.v8
              code:
                local:
                  filename: {filename}
              allow_precompiled: false
"""

service_pos_dict = {
    "rpc_echo_bench": {
        "frontend": "h2",
        "ping": "h3",
    }
}

port_dict = {
    "rpc_echo_bench": {
        "ping": "8081",
        "pong": "8082",
    }
}


def scriptgen_envoy(girs: Dict[str, GraphIR], app: str):
    global local_gen_dir
    local_gen_dir = os.path.join(graph_base_dir, "gen")
    os.makedirs(local_gen_dir, exist_ok=True)

    # compile elements
    compiled_elements = set()
    for gir in girs.values():
        for element in gir.elements["req_client"] + gir.elements["req_server"]:
            if element.lib_name not in compiled_elements:
                compiled_elements.add(element.lib_name)
                impl_dir = os.path.join(local_gen_dir, f"{element.lib_name}_envoy")
                # compile
                execute_local(
                    [
                        "cargo",
                        "build",
                        "--target=wasm32-wasi",
                        "--manifest-path",
                        os.path.join(impl_dir, "Cargo.toml"),
                        "--release",
                    ]
                )
                # copy binary to /tmp
                execute_local(
                    [
                        "cp",
                        os.path.join(
                            impl_dir,
                            f"target/wasm32-wasi/release/{element.lib_name}.wasm",
                        ),
                        "/tmp",
                    ]
                )

    # install elements
    with open(
        os.path.join(Path(__file__).parent, "ping-app-istio-template.yml"), "r"
    ) as f:
        yml_list = list(yaml.safe_load_all(f))
    frontend_deploy, ping_deploy, pong_deploy = yml_list[1], yml_list[3], yml_list[5]
    for gir in girs.values():
        elist = [(e, gir.client) for e in gir.elements["req_client"]] + [
            (e, gir.server) for e in gir.elements["req_server"]
        ]
        for (element, sname) in elist:
            copy_remote_host(
                service_pos_dict[app][sname], f"/tmp/{element.lib_name}.wasm", "/tmp/"
            )
            target_yml = locals()[f"{sname}_deploy"]
            target_yml["spec"]["template"]["spec"]["containers"][1][
                "volumeMounts"
            ].append(
                {
                    "mountPath": f"/etc/{element.lib_name}.wasm",
                    "name": f"{element.lib_name}-wasm",
                }
            )
            target_yml["spec"]["template"]["spec"]["volumes"].append(
                {
                    "hostPath": {
                        "path": f"/tmp/{element.lib_name}.wasm",
                        "type": "File",
                    },
                    "name": f"{element.lib_name}-wasm",
                }
            )
    with open(os.path.join(local_gen_dir, "install.yml"), "w") as f:
        yaml.dump_all(yml_list, f, default_flow_style=False)

    # Kubernetes apply
    kapply(os.path.join(local_gen_dir, "install.yml"))

    # attach elements
    for gir in girs.values():
        elist = [(e, gir.client, "client") for e in gir.elements["req_client"]] + [
            (e, gir.server, "server") for e in gir.elements["req_server"]
        ]
        for (e, sname, placement) in elist:
            contents = {
                "metadata_name": f"{e.lib_name}-{sname}-{placement}",
                "name": f"{e.lib_name}-{placement}",
                "service": sname,
                "bound": "SIDECAR_OUTBOUND"
                if placement == "client"
                else "SIDECAR_INBOUND",
                "port": port_dict[app][gir.server],
                "vmid": f"vm.sentinel.{e.lib_name}-{placement}",
                "filename": f"/etc/{e.lib_name}.wasm",
            }
            attach_path = os.path.join(
                local_gen_dir, f"{e.lib_name}-{placement}-{sname}.yml"
            )
            with open(attach_path, "w") as f:
                f.write(attach_yml.format(**contents))
            kapply(attach_path)
