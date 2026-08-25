"""
rrc_nas_decoder.py

Core LTE RRC/NAS hex decoder. Wraps pycrate to turn raw hex captures
(RRC PDUs on BCCH/PCCH/CCCH/DCCH, or bare NAS messages) into structured
Python dicts, recursively unwrapping any embedded NAS containers and
UE-EUTRA-Capability containers it finds along the way.
"""

import binascii

from pycrate_asn1dir import RRCLTE
from pycrate_mobile import NAS


class RRCNASDecoder:

    def __init__(self):
        # Load RRC definitions once
        self.rrc_defs = RRCLTE.EUTRA_RRC_Definitions

    # ============================================================
    # UNIVERSAL ENTRY POINT
    # ============================================================
    def decode_universal(self, hex_str, layer="RRC", channel="DCCH", direction="UL"):
        # Normalize hex string
        hex_str = (
            hex_str.replace(" ", "")
                   .replace("0x", "")
                   .replace("\n", "")
                   .replace("\r", "")
        )

        try:
            data = binascii.unhexlify(hex_str)
        except Exception as e:
            return {"error": f"Invalid Hex String: {e}"}

        # --- NAS ONLY ---
        if layer.upper() == "NAS":
            nas_decoded = self.decode_nas(data, direction)
            return {"NAS_Message": nas_decoded}

        # --- RRC ---
        elif layer.upper() == "RRC":
            mapping = {
                "DL/BCH": self.rrc_defs.BCCH_BCH_Message,
                "DL/PBCH": self.rrc_defs.BCCH_BCH_Message,
                "DL/BCCH": self.rrc_defs.BCCH_DL_SCH_Message,
                "DL/PCCH": self.rrc_defs.PCCH_Message,
                "DL/CCCH": self.rrc_defs.DL_CCCH_Message,
                "DL/DCCH": self.rrc_defs.DL_DCCH_Message,
                "UL/CCCH": self.rrc_defs.UL_CCCH_Message,
                "UL/DCCH": self.rrc_defs.UL_DCCH_Message,
                "DL/DL-SCH": self.rrc_defs.BCCH_DL_SCH_Message,
                "DL/PDSCH": self.rrc_defs.BCCH_DL_SCH_Message,
                "UL/UE-EUTRA-CAPABILITY": self.rrc_defs.UE_EUTRA_Capability,
            }

            cfg_key = f"{direction.upper()}/{channel.upper()}"
            pdu = mapping.get(cfg_key)

            if not pdu:
                return {"error": f"Unknown RRC configuration: {direction}/{channel}"}

            try:
                # Decode RRC
                pdu.from_uper(data)
                rrc_val = pdu.get_val()

                result = {"RRC_Message": rrc_val}

                # Scan for UE Capability Containers
                decoded_containers = {}
                self.scan_and_decode_capabilities(rrc_val, decoded_containers)
                if decoded_containers:
                    result.update(decoded_containers)

                # Try to find NAS inside RRC (dedicatedInfoNAS, nas_PDU, nas_MessageContainer)
                nas_payload = self.find_nas_container(rrc_val)
                if nas_payload:
                    nas_dec = self.decode_nas(nas_payload, direction)
                    result["INTERIOR_NAS"] = nas_dec

                return result

            except Exception as e:
                return {"error": f"RRC Decode Error: {str(e)}"}

        else:
            return {"error": f"Unknown layer: {layer}"}

    # ============================================================
    # NAS DECODER (STRUCTURED OUTPUT)
    # ============================================================
    def decode_nas(self, data, direction):
        """
        Returns a dict that is easy for LLM/humans to consume:
        - Tries msg.to_dict() first
        - Falls back to msg.show() (string) if needed
        """
        try:
            if direction.upper() == "UL":
                msg, err = NAS.parse_NAS_MO(data)
            else:
                msg, err = NAS.parse_NAS_MT(data)

            if err:
                return {"error": f"NAS Parsing Error: {err}"}

            # Prefer structured representation if available
            try:
                nas_dict = msg.to_dict()
                return {"nas_struct": nas_dict}
            except Exception:
                # Fallback: text dump
                return {"nas_text": msg.show()}

        except Exception as e:
            return {"error": f"NAS Exception: {str(e)}"}

    # ============================================================
    # SEARCH FOR NAS INSIDE RRC
    # ============================================================
    def find_nas_container(self, val):
        """
        Recursively search for NAS payload inside RRC message.
        Handles both:
        - dict[key] == bytes
        - dict[key] == ('dedicatedInfoNAS', bytes)
        """
        if isinstance(val, dict):
            # 1) direct keys
            for k in ['dedicatedInfoNAS', 'nas_PDU', 'nas_MessageContainer']:
                if k in val and isinstance(val[k], (bytes, bytearray)):
                    return val[k]

            # 2) tuple values like: ('dedicatedInfoNAS', <bytes>)
            for v in val.values():
                if (
                    isinstance(v, tuple)
                    and len(v) == 2
                    and v[0] in ['dedicatedInfoNAS', 'nas_PDU', 'nas_MessageContainer']
                    and isinstance(v[1], (bytes, bytearray))
                ):
                    return v[1]

            # 3) recurse deeper
            for v in val.values():
                res = self.find_nas_container(v)
                if res is not None:
                    return res

        elif isinstance(val, (list, tuple)):
            for item in val:
                res = self.find_nas_container(item)
                if res is not None:
                    return res

        return None

    # ============================================================
    # SCAN FOR UE CAPABILITY CONTAINERS
    # ============================================================
    def scan_and_decode_capabilities(self, val, results):
        if isinstance(val, dict):

            if 'ueCapabilityRAT-Container' in val:
                payload = val['ueCapabilityRAT-Container']
                rat_type = val.get('rat-Type', 'unknown')

                if isinstance(payload, bytes) and rat_type == 'eutra':
                    try:
                        rat_pdu = self.rrc_defs.UE_EUTRA_Capability
                        rat_pdu.from_uper(payload)
                        results["INTERIOR_EUTRA_CAPABILITY"] = rat_pdu.get_val()
                    except Exception as err:
                        results["INTERIOR_EUTRA_DECODE_ERROR"] = (
                            f"Failed to parse inner container: {err}"
                        )

            for v in val.values():
                self.scan_and_decode_capabilities(v, results)

        elif isinstance(val, (list, tuple)):
            for item in val:
                self.scan_and_decode_capabilities(item, results)
