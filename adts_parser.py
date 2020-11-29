# https://wiki.multimedia.cx/index.php/ADTS
# https://wiki.multimedia.cx/index.php/MPEG-4_Audio

def parse_adts(buf):
    profile_map = {
            "00": "Main",
            "01": "LC",     # Low Complexity
            "10": "SSR",    # Scalable Sample Rate
            "11": "LTP",    # Long Term Prediction
            }

    freq_index_map = {
            "0000": "96000Hz",
            "0001": "88200Hz",
            "0010": "64000Hz",
            "0011": "48000Hz",
            "0100": "44100Hz",
            "0101": "32000Hz",
            "0110": "24000Hz",
            "0111": "22050Hz",
            "1000": "16000Hz",
            "1001": "12000Hz",
            "1010": "11025Hz",
            "1011": "8000Hz",
            "1100": "7350Hz",
            "1101": "RESERVED",
            "1110": "RESERVED",
            "1111": "EXPLICIT",
            }

    ch_conf_map = {
            "000": "PCE",
            "001": "1ch",
            "010": "2ch",
            "011": "3ch",
            "100": "4ch",
            "101": "5ch",
            "110": "5.1ch",
            "111": "7.1ch",
            }

    h = bin(int.from_bytes(buf[:7],"big"))[2:].rjust(56,"0")
    return {
            "header_length": 7 if h[15] == "1" else 9,
            "version": "MP4" if h[12] == "1" else "MP2",
            "b_crc_absent": int(h[15]), # 0:CRC 1:No-CRC
            "profile": profile_map.get(h[16:18]),
            "freq": freq_index_map.get(h[18:22]),
            "b_private_bit": int(h[22]),
            "ch_conf": ch_conf_map.get(h[23:26]),
            "b_originality": int(h[26]),
            "b_home": int(h[27]),
            "b_crid_bit": int(h[28]),
            "b_crid_start": int(h[29]),
            "frame_length": int(h[30:43],2),
            "buffer_fullness": int(h[43:54],2),
            "nb_aac_frames": 1 + int(h[54:56],2), # nb of AAC frames - 1
            }

adts_hdr = {
        "offset": "Offset",
        "header_length": "HL",
        "version": "Ver",
        "b_crc_absent": "C",
        "profile": "Prof",
        "freq": "Freq",
        "b_private_bit": "P",
        "ch_conf": "Conf",
        "b_originality": "O",
        "b_home": "H",
        "b_crid_bit": "C",
        "b_crid_start": "C",
        "frame_length": "FrameLen",
        "buffer_fullness": "Buffers",
        "nb_aac_frames": "AC",
        }

adts_fmt = "{offset:8} {header_length:2} {version:3} {b_crc_absent:1} {profile:4} {freq:8} {b_private_bit:1} {ch_conf:5} {b_originality:1} {b_home:1} {b_crid_bit:1} {b_crid_start:1} {frame_length:6} {buffer_fullness:6} {nb_aac_frames:2}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: adts_parser (file)")
        exit(0)
    else:
        buf = open(sys.argv[1], "rb").read()
        print(adts_fmt.format(**adts_hdr))
        i = 0
        while i < len(buf):
            hdr = parse_adts(buf[i:])
            hdr.update({"offset":i})
            print(adts_fmt.format(**hdr))
            i += hdr["frame_length"]

