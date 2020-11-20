MP4 parser
==========

## Example

```
% python mp4parser.py test.mp4
file size: 740890
+ ftyp: 32
+ free: 8
+ mdat: 725361
+ moov: 15489
    + mvhd: 108
    + trak: 6298
        + tkhd: 92
        + edts: 36
            + elst: 28
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
    + trak: 8977
        + tkhd: 92
        + edts: 36
            + elst: 28
        + mdia: 8841
            + mdhd: 32
            + hdlr: 45
            + minf: 8756
                + smhd: 16
                + dinf: 36
                    + dref: 28
                + stbl: 8696
                    + stsd: 106
                    + stts: 32
                    + stsc: 3316
                    + stsz: 3776
                    + stco: 1404
                    + sgpd: 26
                    + sbgp: 28
    + udta: 98
```
