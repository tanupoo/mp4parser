import os
import argparse
import json

# ISO/IEC 14496-12-2005
# ISO/IEC 14496-1

"""
remaining_size = fd.tell()

body_size = (box_size in the box header) - (box header length)

    + tkhd:
        width, height: For non-visual tracks (e.g. audio), should be set to 0.
    + mdia: 6162
        + mdhd: 32
        + hdlr: 45
        + minf: 6077
            + vmhd: 20
            + dinf: 36
                + dref: 28
            + stbl: 6013
                + stsd: 157
                + stts: 24
                + stss: 28
                + ctts: 2872
                + stsc: 64
                + stsz: 1460
                + stco: 1400

vmhd: Video Media Header Box
    graphicsmode: 0, copy over the existing image
    opcolor: red, green, blue for use by graphics modes, 0

smhd: Sound Media Header Box
    balance: a fixed-point 8.8 number, 0 is centre.

stts: Decoding Time to Sample Box
    DT(n+1) = DT(n) + STTS(n)
    DT(i) = SUM(for j=0 to i-1 of delta(j))
    entry_count: an integer, gives the number of entries.
    sample_count: an integer, counts the number of consecutive samples
        that have the given duration.
    sample_delta: an integer, the delta of these samples in the
        time-scale of the media.

stco: Chunk Offset Box
    Offsets are file offsets, not the offset into any box within the file (e.g.
    Media Data Box).
    chunk_offset;
        the offset of the start of a chunk into its containing media file.

stsz: Sample Size Boxes
    sample_size: an integer, the default sample size.
        0: the samples have different sizes, and those sizes are stored
            in the sample size table.
        not 0: all the samples are the same size and no array follows.
            XXX indicating sample_count is 0 ?
    sample_count: integer that gives the number of samples in the track.
        not 0: the number of entries in the following table.  sample_size is 0.
        0: XXX
    entry_size: an integer specifying the size of a sample,
        indexed by its number.

stsc: Sample To Chunk Box
    Samples within the media data are grouped into chunks. Chunks can be of
    different sizes, and the samples within a chunk can have different
    sizes.
    You can convert this to a sample count by multiplying by the appropriate
    samples- per-chunk.
    entry_count: an integer, the number of entries in the following table.
    first_chunk: an integer, the index of the first chunk in this run of chunks
        that share the same samples-per-chunk and sample-description-index;
        the index of the first chunk in a track has the value 1
        (the first_chunk field in the first record of this box has the value 1,
        identifying that the first sample maps to the first chunk).
    samples_per_chunk: an integer, the number of samples in each of these
        chunks.
    sample_description_index is an integer that gives the index
        of the sample entry that describes the samples in this chunk.
        The index ranges from 1 to the number of sample entries in the Sample
        Description Box.

"""

g_sample = None # placeholder, initialized at parse_trak()
g_traks = {}

def indent(depth):
    return "  "*depth

def decode_int(v_raw, signed=False):
    return int.from_bytes(v_raw, "big", signed=signed)

def decode_str(v_raw, signed=False):
    try:
        return v_raw.decode().replace("\x00","")
    except UnicodeDecodeError:
        return "(ERR)"

def decode_hex(v_raw, signed=False):
    return "0x" + "".join([ "{:02x}".format(i) for i in v_raw ])

def print_array1(depth, v_name, v_val, v_raw, offset, nb_item):
    print(f"{indent(depth)}{v_name}({nb_item:02}): {v_val}", end="")
    print(f" :: 0x{v_raw.hex()} offset={offset}" if opt.debug else "")

def print_val(depth, v_name, v_val, v_raw, offset):
    print(f"{indent(depth)}{v_name}: {v_val}", end="")
    print(f" :: 0x{v_raw.hex()} offset={offset}" if opt.debug else "")

def parse_base(fd, depth, offset, v_name, v_size, v_buf_size, decode_func,
               signed=False):
    """
    Note: uses bytes size though the spec uses in bit size.
    e.g.
    v_size      4 bytes |----|
    v_buf_size 16 bytes |----|----|----|----|
    """
    if v_buf_size is not None:
        for i in range(0, v_buf_size, v_size):
            v_raw = fd.read(v_size)
            v_val = decode_func(v_raw, signed=signed)
            print_array1(depth, v_name, v_val, v_raw, offset, i//v_size)
            offset += v_size
    else:
        v_raw = fd.read(v_size)
        v_val = decode_func(v_raw, signed=signed)
        print_val(depth, v_name, v_val, v_raw, offset)
        offset += v_size
    return v_val, offset

def parse_int(fd, depth, offset, v_name, v_size, v_buf_size=None, signed=False):
    return parse_base(fd, depth, offset, v_name, v_size, v_buf_size, decode_int,
                      signed=signed)

def parse_str(fd, depth, offset, v_name, v_size, v_buf_size=None):
    return parse_base(fd, depth, offset, v_name, v_size, v_buf_size, decode_str)

def parse_hex(fd, depth, offset, v_name, v_size, v_buf_size=None):
    return parse_base(fd, depth, offset, v_name, v_size, v_buf_size, decode_hex)

def get_str_null(fd, offset, max_size):
    buf = []
    while max_size > offset:
        a = fd.read(1)
        offset += 1
        if a == b"\x00":
            break
        buf.append(a)
    name = b"".join(buf).decode()
    return name, offset

def parse_fullbox(fd, depth, offset):
    """
    Note: assuming that the former part (i.e. Box) has been parsed before.
        only parse version and flags.
    aligned(8) class FullBox(unsigned int(32) boxtype,
                             unsigned int(8) v,
                             bit(24) f)
                     extends Box(boxtype) {
        unsigned int(8) version = v;
        bit(24) flags = f;
    }
    """
    version, offset = parse_int(fd, depth, offset, "version", 1)
    flags, offset = parse_hex(fd, depth, offset, "flags", 3)
    return version, flags, offset

def parse_sample_entry(fd, depth, offset):
    """
    aligned(8) abstract class SampleEntry (unsigned int(32) format)
                              extends Box(format) {
        const unsigned int(8)[6] reserved = 0;
        unsigned int(16) data_reference_index;
    }
    """
    v, offset = parse_hex(fd, depth, offset, "reserved", 6) # 8 * 6 / 8
    v, offset = parse_int(fd, depth, offset, "data_reference_index", 2)
    return offset

def check_remaining(fd, depth, body_size, offset):
    if body_size > offset:
        print(f"{indent(depth)}==> body_size {body_size} != offset {offset}")
        v, offset = parse_hex(fd, depth+1, offset, "remaining", body_size-offset)
    elif body_size < offset:
        raise ValueError(f"body_size {body_size} < offset {offset}")

#
# boxes parser
#
def parse_gen(fd, depth, body_size):
    buf = fd.read(body_size)
    if opt.debug:
        print(f"{indent(depth)}gen: 0x{buf.hex()}")

def parse_trak(fd, depth, body_size):
    """
    aligned(8) class TrackBox extends Box(‘trak’) { }
    """
    global g_sample
    g_sample = {}
    mp4parse(fd, depth+1, body_size)
    if opt.save_stbl:
        g_traks.update({g_sample["track_id"]:
                        g_sample.copy()}) # enough to shallow copy.

def parse_con(fd, depth, body_size):
    """
    aligned(8) class MovieBox extends Box(‘moov’) { }
    aligned(8) class MediaBox extends Box(‘mdia’) { }
    aligned(8) class EditBox extends Box(‘edts’) { }
    aligned(8) class DataInformationBox extends Box(‘dinf’) { }
    aligned(8) class SampleTableBox extends Box(‘stbl’) { }
    """
    mp4parse(fd, depth+1, body_size)

def parse_mdat(fd, depth, body_size):
    """
    aligned(8) class MediaDataBox
                     extends Box(‘mdat’) {
        bit(8) data[];
    }
    """
    if opt.save_stbl:
        g_traks.update({"mdat_offset": fd.tell()})
    if opt.save_mdat:
        with open(opt.save_mdat, "wb") as fd_dst:
            max_read_size = 16*1024
            while body_size > 0:
                buf = fd.read(min([max_read_size,body_size]))
                if not buf:
                    break
                fd_dst.write(buf)
                body_size -= max_read_size
    else:
        fd.read(body_size)

def parse_mdhd(fd, depth, body_size):
    """
    aligned(8) class MediaHeaderBox
                     extends FullBox(‘mdhd’, version, 0) {
        if (version==1) {
            unsigned int(64) creation_time;
            unsigned int(64) modification_time;
            unsigned int(32) timescale;
            unsigned int(64) duration;
        } else { // version==0
            unsigned int(32) creation_time;
            unsigned int(32) modification_time;
            unsigned int(32) timescale;
            unsigned int(32) duration;
        }
        bit(1)   pad = 0;
        unsigned int(5)[3] language; // ISO-639-2/T language code
        unsigned int(16) pre_defined = 0;
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    if version == 1:
        v, offset = parse_int(fd, depth, offset, "creation_time", 8)
        v, offset = parse_int(fd, depth, offset, "modification_time", 8)
        v, offset = parse_int(fd, depth, offset, "timescale", 4)
        v, offset = parse_int(fd, depth, offset, "duration", 8)
    elif version == 0:
        v, offset = parse_int(fd, depth, offset, "creation_time", 4)
        v, offset = parse_int(fd, depth, offset, "modification_time", 4)
        v, offset = parse_int(fd, depth, offset, "timescale", 4)
        v, offset = parse_int(fd, depth, offset, "duration", 4)
    else:
        raise ValueError(f"unknown version {version}")
    #
    v_raw = fd.read(2)
    buf = bin(decode_int(v_raw))[2:].rjust(16,"0")
    print_val(depth, "pad", "b"+buf[0], v_raw, offset)
    for i in range(3):
        print_array1(depth, "language", "b"+buf[i:i+5], v_raw, offset, i)
    offset += 2
    #
    v, offset = parse_int(fd, depth, offset, "pre_defined", 2)
    check_remaining(fd, depth, body_size, offset)

def parse_hdlr(fd, depth, body_size):
    """
    aligned(8) class HandlerBox
                     extends FullBox(‘hdlr’, version = 0, 0) {
        unsigned int(32) pre_defined = 0;
        unsigned int(32) handler_type;
        const unsigned int(32)[3] reserved = 0;
        string   name;
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    v, offset = parse_int(fd, depth, offset, "pre_defined", 4)
    v, offset = parse_int(fd, depth, offset, "handler_type", 4)
    v, offset = parse_int(fd, depth, offset, "reserved", 4, 12)
    v, offset = parse_str(fd, depth, offset, "name", body_size-offset)

def parse_tkhd(fd, depth, body_size):
    """
    aligned(8) class TrackHeaderBox
                     extends FullBox(‘tkhd’, version, flags) {
        if (version==1) {
            unsigned int(64) creation_time;
            unsigned int(64) modification_time;
            unsigned int(32) track_ID;
            const unsigned int(32) reserved = 0;
            unsigned int(64) duration;
        } else { // version==0
            unsigned int(32) creation_time;
            unsigned int(32) modification_time;
            unsigned int(32) track_ID;
            const unsigned int(32) reserved = 0;
            unsigned int(32) duration;
        }
        const unsigned int(32)[2] reserved = 0;
        template int(16) layer = 0;
        template int(16) alternate_group = 0;
        template int(16) volume = { if track_is_audio 0x0100 else 0};
        const unsigned int(16) reserved = 0;
        template int(32)[9] matrix=
            { 0x00010000,0,0,0,0x00010000,0,0,0,0x40000000 };
            // unity matrix
        unsigned int(32) width;
        unsigned int(32) height;
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    if version == 1:
        v, offset = parse_int(fd, depth, offset, "creation_time", 8)
        v, offset = parse_int(fd, depth, offset, "modification_time", 8)
        track_id, offset = parse_int(fd, depth, offset, "trackID", 4)
        v, offset = parse_int(fd, depth, offset, "reserved", 4)
        v, offset = parse_int(fd, depth, offset, "duration", 8)
    elif version == 0:
        v, offset = parse_int(fd, depth, offset, "creation_time", 4)
        v, offset = parse_int(fd, depth, offset, "modification_time", 4)
        track_id, offset = parse_int(fd, depth, offset, "trackID", 4)
        v, offset = parse_int(fd, depth, offset, "reserved", 4)
        v, offset = parse_int(fd, depth, offset, "duration", 4)
    else:
        raise ValueError(f"unknown version {version}")
    v, offset = parse_int(fd, depth, offset, "reserved", 4, 8)
    v, offset = parse_int(fd, depth, offset, "layer", 2)
    v, offset = parse_int(fd, depth, offset, "alternate_group", 2)
    v, offset = parse_int(fd, depth, offset, "volume", 2)
    v, offset = parse_int(fd, depth, offset, "reserved", 2)
    v, offset = parse_hex(fd, depth, offset, "matrix", 4, 36)
    v, offset = parse_int(fd, depth, offset, "width", 4)
    v, offset = parse_int(fd, depth, offset, "height", 4)
    g_sample.setdefault("track_id", track_id)
    check_remaining(fd, depth, body_size, offset)

def parse_vmhd(fd, depth, body_size):
    """
    aligned(8) class VideoMediaHeaderBox
                     extends FullBox(‘vmhd’, version = 0, 1) {
        template unsigned int(16) graphicsmode = 0; // copy, see below
        template unsigned int(16)[3] opcolor = {0, 0, 0};
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    v, offset = parse_int(fd, depth, offset, "graphicsmode", 2)
    v, offset = parse_int(fd, depth, offset, "opcolor", 2, 6)
    g_sample.setdefault("media", "video")
    check_remaining(fd, depth, body_size, offset)

def parse_smhd(fd, depth, body_size):
    """
    aligned(8) class SoundMediaHeaderBox
        extends FullBox(‘smhd’, version = 0, 0) {
        template int(16) balance = 0;
        const unsigned int(16) reserved = 0;
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    v, offset = parse_int(fd, depth, offset, "balance", 2)
    v, offset = parse_int(fd, depth, offset, "reserved", 2)
    g_sample.setdefault("media", "audio")
    check_remaining(fd, depth, body_size, offset)

def parse_elst(fd, depth, body_size):
    """
    aligned(8) class EditListBox
                     extends FullBox(‘elst’, version, 0) {
        unsigned int(32) entry_count;
        for (i=1; i <= entry_count; i++) {
            if (version==1) {
                unsigned int(64) segment_duration;
                int(64) media_time;
            } else { // version==0
                unsigned int(32) segment_duration;
                int(32) media_time;
            }
            int(16) media_rate_integer;
            int(16) media_rate_fraction = 0;
        }
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    v, offset = parse_int(fd, depth, offset, "entry_count", 4)
    if version == 1:
        v, offset = parse_int(fd, depth, offset, "segment_duration", 8)
        v, offset = parse_int(fd, depth, offset, "media_time", 8)
    elif version == 0:
        v, offset = parse_int(fd, depth, offset, "segment_duration", 4)
        v, offset = parse_int(fd, depth, offset, "media_time", 4)
    else:
        raise ValueError(f"unknown version {version}")
    v, offset = parse_int(fd, depth, offset, "media_rate_integer", 2)
    v, offset = parse_int(fd, depth, offset, "media_rate_fraction", 2)
    check_remaining(fd, depth, body_size, offset)

def parse_dref(fd, depth, body_size):
    """
    aligned(8) class DataEntryUrlBox (bit(24) flags)
        extends FullBox(‘url ’, version = 0, flags) {
        string location;
    }
    aligned(8) class DataEntryUrnBox (bit(24) flags)
        extends FullBox(‘urn ’, version = 0, flags) {
        string name;
        string location;
    }
    aligned(8) class DataReferenceBox
        extends FullBox(‘dref’, version = 0, 0) {
        unsigned int(32) entry_count;
        for (i=1; i <= entry_count; i++) {
            DataEntryBox(entry_version, entry_flags) data_entry;
        }
    }
    DataEntryBox:
        int(8) entry_version;
        int(24) entry_flags;
        string data_entry;  // URL or URN, UTF-8
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    entry_count, offset = parse_int(fd, depth, offset, "entry_count", 4)
    while body_size > offset and entry_count > 0:
        version, flags, offset = parse_fullbox(fd, depth+1, offset)
        name, offset = get_str_null(fd, offset, body_size)
        print(f"{indent(depth+1)}entry {entry_count}:{name}")
        entry_count -= 1
    check_remaining(fd, depth, body_size, offset)

def parse_stsd(fd, depth, body_size):
    """
    class BitRateBox extends Box(‘btrt’) {
        unsigned int(32) bufferSizeDB;
        unsigned int(32) maxBitrate;
        unsigned int(32) avgBitrate;
    }
    aligned(8) class SampleDescriptionBox (unsigned int(32) handler_type)
                     extends FullBox('stsd', version, 0) {
        int i ;
        unsigned int(32) entry_count;
        for (i = 1 ; i <= entry_count ; i++) {
            SampleEntry(); // an instance of a class derived from SampleEntry
        }
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    entry_count, offset = parse_int(fd, depth, offset, "entry_count", 4)
    for i in range(entry_count):
        box_type, box_size, box_hdr_size = parse_box(fd, depth, body_size)
        sample_hdr_size  = parse_sample_entry(fd, depth+1, 0)
        pf_tab.get(box_type, parse_gen)(fd, depth+1,
                                        box_size-box_hdr_size-sample_hdr_size)
        offset += box_size
    check_remaining(fd, depth, body_size, offset)

def decode_sample_dt(vals):
    stts = []
    for count,delta in vals:
        for j in range(count):
            stts.append(delta)
    g_sample.setdefault("stts", stts)
    return sum(stts)

def parse_stts(fd, depth, body_size):
    """
    aligned(8) class TimeToSampleBox
        extends FullBox(’stts’, version = 0, 0) {
        unsigned int(32) entry_count;
        int i;
        for (i=0; i < entry_count; i++) {
            unsigned int(32) sample_count;
            unsigned int(32) sample_delta;
        }
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    entry_count, offset = parse_int(fd, depth, offset, "entry_count", 4)
    vals = []
    for i in range(entry_count):
        sample_count, offset = parse_int(fd, depth+1, offset, "sample_count", 4)
        sample_delta, offset = parse_int(fd, depth+1, offset, "sample_delta", 4)
        vals.append((sample_count, sample_delta))
    duration = decode_sample_dt(vals)
    print(f"{indent(depth+1)}sum of delta: {duration}")
    check_remaining(fd, depth, body_size, offset)

def parse_stss(fd, depth, body_size):
    """
    aligned(8) class SyncSampleBox
        extends FullBox(‘stss’, version = 0, 0) {
        unsigned int(32) entry_count;
        int i;
        for (i=0; i < entry_count; i++) {
            unsigned int(32) sample_number;
        }
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    entry_count, offset = parse_int(fd, depth, offset, "entry_count", 4)
    for i in range(entry_count):
        v, offset = parse_int(fd, depth+1, offset, "sample_number", 4)
    check_remaining(fd, depth, body_size, offset)

    """
    timescale = 1000
    duration = 60064
    sample_count = 360
    sample_delta = 2048
    CT(n) = DT(n) + CTTS(n)
        ctts
    """

def parse_ctts(fd, depth, body_size):
    """
    aligned(8) class CompositionOffsetBox
        extends FullBox(‘ctts’, version, 0) {
        unsigned int(32) entry_count;
        int i;
        if (version==0) {
            for (i=0; i < entry_count; i++) {
                unsigned int(32) sample_count;
                unsigned int(32) sample_offset;
            }
        } else if (version == 1) {
            for (i=0; i < entry_count; i++) {
                unsigned int(32) sample_count;
                signed int(32) sample_offset;
            }
        }
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    entry_count, offset = parse_int(fd, depth, offset, "entry_count", 4)
    if version == 0:
        for i in range(entry_count):
            v, offset = parse_int(fd, depth+1, offset, "sample_count", 4)
            v, offset = parse_int(fd, depth+1, offset, "sample_offset", 4)
    elif version == 1:
        for i in range(entry_count):
            v, offset = parse_int(fd, depth+1, offset, "sample_count", 4)
            v, offset = parse_int(fd, depth+1, offset, "sample_offset", 4,
                                  signed=True)
    else:
        raise ValueError(f"unknown version {version}")
    check_remaining(fd, depth, body_size, offset)

def decode_chunk_samples(vals):
    """
    decoding Sample to Chunk (stsc)
    """
    stsc = []
    n = 0
    n,nb_samples = vals.pop(0)
    for next_chunk_num,next_nb_samples in vals:
        while next_chunk_num > n:
            stsc.append(nb_samples)
            n += 1
        nb_samples = next_nb_samples
    stsc.append(next_nb_samples)
    g_sample.setdefault("stsc", stsc)

def parse_stsc(fd, depth, body_size):
    """
    aligned(8) class SampleToChunkBox
        extends FullBox(‘stsc’, version = 0, 0) {
        unsigned int(32) entry_count;
        for (i=1; i <= entry_count; i++) {
            unsigned int(32) first_chunk;
            unsigned int(32) samples_per_chunk;
            unsigned int(32) sample_description_index;
        }
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    entry_count, offset = parse_int(fd, depth, offset, "entry_count", 4)
    vals = []
    for i in range(entry_count):
        first_chunk, offset = parse_int(fd, depth+1, offset,
                                        f"first_chunk[{i}]", 4)
        samples_per_chunk, offset = parse_int(fd, depth+1, offset,
                                              f"samples_per_chunk[{i}]", 4)
        v, offset = parse_int(fd, depth+1, offset,
                              f"sample_description_index[{i}]", 4)
        vals.append((first_chunk,samples_per_chunk))
    decode_chunk_samples(vals)
    check_remaining(fd, depth, body_size, offset)

def parse_stsz(fd, depth, body_size):
    """
    aligned(8) class SampleSizeBox
        extends FullBox(‘stsz’, version = 0, 0) {
        unsigned int(32) sample_size;
        unsigned int(32) sample_count;
        if (sample_size==0) {
            for (i=1; i <= sample_count; i++) {
                unsigned int(32) entry_size;
            }
        }
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    sample_size, offset = parse_int(fd, depth, offset, "sample_size", 4)
    sample_count, offset = parse_int(fd, depth, offset, "sample_count", 4)
    vals = []
    if sample_size == 0:
        total_entry_size = 0
        for i in range(sample_count):
            entry_size, offset = parse_int(fd, depth+1, offset,
                                           f"entry_size[{i}]", 4)
            vals.append(entry_size)
            total_entry_size += entry_size
    else:
        for i in range(sample_count):
            vals.append(sample_size)
        total_entry_size = sample_size*sample_count
    print(f"{indent(depth)}total_entry_size: {total_entry_size}")
    g_sample.setdefault("stsz", vals)
    check_remaining(fd, depth, body_size, offset)

def parse_stco(fd, depth, body_size):
    """
    aligned(8) class ChunkOffsetBox
        extends FullBox(‘stco’, version = 0, 0) {
        unsigned int(32) entry_count;
        for (i=1; i <= entry_count; i++) {
            unsigned int(32) chunk_offset;
        }
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    entry_count, offset = parse_int(fd, depth, offset, "entry_count", 4)
    vals = []
    for i in range(entry_count):
        chunk_offset, offset = parse_int(fd, depth+1, offset,
                                         f"chunk_offset[{i}]", 4)
        vals.append(chunk_offset)
    g_sample.setdefault("stco", vals)
    check_remaining(fd, depth, body_size, offset)

def parse_sgpd(fd, depth, body_size):
    """
    abstract class SampleGroupDescriptionEntry (unsigned int(32) grouping_type)
    {
    }
    aligned(8) class SampleGroupDescriptionBox (unsigned int(32) handler_type)
        extends FullBox('sgpd', version, 0) {
        unsigned int(32) grouping_type;
        if (version==1) {
            unsigned int(32) default_length;
        } else if (version>=2) {
            unsigned int(32) default_sample_description_index;
        }
        unsigned int(32) entry_count;
        int i;
        for (i = 1 ; i <= entry_count ; i++) {
            if (version==1) {
                if (default_length==0) {
                    unsigned int(32) description_length;
                }
            }
            SampleGroupEntry (grouping_type);
        }
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    grouping_type, offset = parse_int(fd, depth, offset, "grouping_type", 4)
    if version == 1:
        default_length, offset = parse_int(fd, depth, offset, "default_length", 4)
    elif version > 1:
        v, offset = parse_int(fd, depth, offset,
                              "default_sample_description_index", 4)
    else:
        raise ValueError(f"unknown version {version}")
    entry_count, offset = parse_int(fd, depth, offset, "entry_count", 4)
    for i in range(entry_count):
        if version == 1:
            if default_length == 0:
                v, offset = parse_int(fd, depth+1, offset, "description_length", 4)
    check_remaining(fd, depth, body_size, offset)

def parse_sbgp(fd, depth, body_size):
    """
    aligned(8) class SampleToGroupBox
        extends FullBox(‘sbgp’, version, 0) {
        unsigned int(32) grouping_type;
        if (version == 1) {
            unsigned int(32) grouping_type_parameter;
        }
        unsigned int(32) entry_count;
        for (i=1; i <= entry_count; i++) {
            unsigned int(32) sample_count;
            unsigned int(32) group_description_index;
        }
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    grouping_type, offset = parse_int(fd, depth, offset, "grouping_type", 4)
    if version == 1:
        grouping_type_parameter, offset = parse_int(fd, depth, offset,
                                                    "grouping_type_parameter", 4)
    entry_count, offset = parse_int(fd, depth, offset, "entry_count", 4)
    for i in range(entry_count):
        v, offset = parse_int(fd, depth, offset, "sample_count", 4)
        v, offset = parse_int(fd, depth, offset, "group_description_index", 4)
    check_remaining(fd, depth, body_size, offset)

def parse_meta(fd, depth, body_size):
    """
    aligned(8) class MetaBox (handler_type)
        extends FullBox(‘meta’, version = 0, 0) {
        HandlerBox(handler_type) theHandler;
        PrimaryItemBox primary_resource;
        DataInformationBox file_locations;
        ItemLocationBox item_locations;
        ItemProtectionBox protections;
        ItemInfoBox item_infos;
        IPMPControlBox IPMP_control;
        ItemReferenceBox item_refs;
        ItemDataBox item_data;
        Box   other_boxes[];
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    parse_con(fd, depth, body_size-offset)

def parse_icpv(fd, depth, body_size):
    """
    class IncompleteAVCSampleEntry()
        extends VisualSampleEntry (‘icpv’){
        CompleteTrackInfoBox();
        AVCConfigurationBox config;
        MPEG4BitRateBox (); // optional
        MPEG4ExtensionDescriptorsBox (); // optional
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    entry_count, offset = parse_int(fd, depth, offset, "entry_count", 4)
    for i in range(entry_count):
        v, offset = parse_int(fd, depth+1, offset, f"chunk_offset[{i}]", 4)
    check_remaining(fd, depth, body_size, offset)

def parse_ftyp(fd, depth, body_size):
    """
    aligned(8) class FileTypeBox
        extends Box(‘ftyp’) {
        unsigned int(32) major_brand;
        unsigned int(32) minor_version;
        unsigned int(32) compatible_brands[]; // to end of the box
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    v, offset = parse_str(fd, depth, 0, "major_brand", 4)
    v, offset = parse_hex(fd, depth, offset, "minor_versions", 4)
    v, offset = parse_str(fd, depth, offset, "compatible_brands", 4,
                          body_size-offset)
    check_remaining(fd, depth, body_size, offset)

def parse_mvhd(fd, depth, body_size):
    """
    aligned(8) class MovieHeaderBox
                     extends FullBox(‘mvhd’, version, 0) {
        if (version==1) {
            unsigned int(64) creation_time; 
            nsigned int(64) modification_time;
            unsigned int(32) timescale;
            unsigned int(64) duration;
        } else { // version==0
            unsigned int(32) creation_time;
            unsigned int(32) modification_time;
            unsigned int(32) timescale;
            unsigned int(32) duration;
        }
        template int(32) rate = 0x00010000; // typically 1.0
        template int(16) volume = 0x0100; // typically, full volume
        const bit(16) reserved = 0;
        const unsigned int(32)[2] reserved = 0;
        template int(32)[9] matrix =
            { 0x00010000,0,0,0,0x00010000,0,0,0,0x40000000 };
            // Unity matrix
        bit(32)[6] pre_defined = 0;
        unsigned int(32) next_track_ID;
    }
    """
    if not opt.verbose:
        fd.read(body_size)
        return
    version, flags, offset = parse_fullbox(fd, depth, 0)
    if version == 1:
        v, offset = parse_int(fd, depth, offset, "creation_time", 8)
        v, offset = parse_int(fd, depth, offset, "modification_time", 8)
        v, offset = parse_int(fd, depth, offset, "timescale", 4)
        v, offset = parse_int(fd, depth, offset, "duration", 8)
    elif version == 0:
        v, offset = parse_int(fd, depth, offset, "creation_time", 4)
        v, offset = parse_int(fd, depth, offset, "modification_time", 4)
        v, offset = parse_int(fd, depth, offset, "timescale", 4)
        v, offset = parse_int(fd, depth, offset, "duration", 4)
    else:
        raise ValueError(f"unknown version {version}")
    v, offset = parse_hex(fd, depth, offset, "rate", 4)
    v, offset = parse_hex(fd, depth, offset, "volume", 2)
    v, offset = parse_int(fd, depth, offset, "reserved", 2)
    v, offset = parse_int(fd, depth, offset, "reserved", 4)
    v, offset = parse_int(fd, depth, offset, "reserved", 4)
    v, offset = parse_hex(fd, depth, offset, "matrix", 4, 36)
    v, offset = parse_int(fd, depth, offset, "pre_defined", 4, 24)
    v, offset = parse_int(fd, depth, offset, "next_track_ID", 4)
    check_remaining(fd, depth, body_size, offset)

# parsing function table
pf_tab = {
        "ftyp": parse_ftyp,
        "mdat": parse_mdat,
        "moov": parse_con,
        "mvhd": parse_mvhd,
        "iods": parse_gen, # spec ?
        "trak": parse_trak,
        "tkhd": parse_tkhd,
        "edts": parse_con,
        "elst": parse_elst,
        "mdia": parse_con,
        "mdhd": parse_mdhd,
        "hdlr": parse_hdlr,
        "minf": parse_con,
        "vmhd": parse_vmhd,
        "smhd": parse_smhd,
        "dinf": parse_con,
        "stbl": parse_con, 
        "dref": parse_dref,
        "stsd": parse_stsd,
        "stts": parse_stts,
        "stss": parse_stss,
        "ctts": parse_ctts,
        "stsc": parse_stsc,
        "stsz": parse_stsz,
        "stco": parse_stco,
        "avc1": parse_gen,
        "mp4a": parse_gen,
        "sgpd": parse_sgpd,
        "sbgp": parse_sbgp,
        "udta": parse_con,
        "meta": parse_meta,
        }

def parse_box(fd, depth, rem_size):
    """
    aligned(8) class Box (unsigned int(32) boxtype,
                          optional unsigned int(8)[16] extended_type) {
        unsigned int(32) size;
        unsigned int(32) type = boxtype;
        if (size==1) {
            unsigned int(64) largesize;
        } else if (size==0) {
            // box extends to end of file
        }
        if (boxtype==‘uuid’) {
            unsigned int(8)[16] usertype = extended_type;
        }
    }

    rem_size: size of the buffer from the begining to the end.
    """
    # box size and type.
    box_size = decode_int(fd.read(4))
    box_type = decode_str(fd.read(4))
    box_hdr_size = 8
    # box size or extended box size.
    box_size_extended = False
    if box_size == 1:
        box_size = decode_int(fd.read(8))
        box_size_extended = True
        box_hdr_size += 8
    elif box_size == 0:
        box_size = rem_size
    # extended box type.
    box_type_uuid = False
    if box_type == "uuid":
        uuid_box_type = decode_str(fd.read(8))
        box_type_uuid = True
        box_hdr_size += 8
    #
    print(f"{indent(depth)}+ {box_type}: {box_size}"
            "{}".format(" E" if box_size_extended else ""), end="")
    print(f" hdr_size={box_hdr_size}" if opt.debug else "")
    return box_type, box_size, box_hdr_size

def mp4parse(fd, depth, rem_size):
    while rem_size > 0:
        box_type, box_size, box_hdr_size = parse_box(fd, depth, rem_size)
        pf_tab.get(box_type, parse_gen)(fd, depth+1, box_size-box_hdr_size)
        # cal remaining size.
        if rem_size < box_size:
            raise ValueError(f"box_size is too big, {box_size} > {rem_size}")
        rem_size -= box_size

#
# parser main
#
from argparse import ArgumentParser
from argparse import ArgumentDefaultsHelpFormatter
ap = ArgumentParser(
        description="a parser for MP4 format.",
        formatter_class=ArgumentDefaultsHelpFormatter)
ap.add_argument("mp4file", help="MP4 file.")
ap.add_argument("--save-mdat", action="store", dest="save_mdat",
                help="specify a file name to store mdat.")
ap.add_argument("--save-stbl", action="store", dest="save_stbl",
                help="specify a file name to store stbl.")
ap.add_argument("-v", action="store_true", dest="verbose",
                help="enable verbose mode.")
ap.add_argument("-d", action="store_true", dest="debug",
                help="enable debug mode.")
opt = ap.parse_args()

if opt.save_mdat or opt.save_stbl:
    # enable verbose mode. to store mdat or stbl, need to parse detail.
    opt.verbose = True

file_size = os.stat(opt.mp4file).st_size
print(f"file size: {file_size}")
with open(opt.mp4file, "rb") as fd:
    mp4parse(fd, 0, file_size)

if opt.save_stbl:
    with open(opt.save_stbl, "w") as fd_stbl:
        json.dump(g_traks, fd_stbl)
