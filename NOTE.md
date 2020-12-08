
## Links

- https://mpeg.chiariglione.org/standards/mpeg-4

## moov:mvhd

- timescale: 時刻計測の単位。単位は1/N秒。
    e.g. 1000 であれば 1/1000 秒。
- duration: 記録されたトラックのうち一番長い時間。N/timescale 
    e.g. 30064 で timescale=1000 あれば 30.064 秒。
- rate: 再生速度。16ビット.16ビットで表現されている。
    e.g. 初期値 0x00010000 = 1.0
- volume: 再生音量。8ビット.8ビットで表現されている。
    e.g. 初期値 0x0100 = 1.0

## moov:trak:tkhd

- width: ビデオトラックの幅。オーディオトラックならば 0
- height: ビデオトラックの高さ。オーディオトラックならば 0

## moov:trak:mdia:mdhd の構造

- timescale: 時刻計測の単位。単位は1/N秒。
    + e.g. 12800
- duration: トラックの時間。N/timescale 
    + e.g. 384000 で scale=12800 ならば 30.0 秒
    + e.g. 481024 で scale=16000 ならば 30.064 秒

## moov:trak:mdia:minf

- vmhd があればビデオトラック
- smhd があればオーディオトラック

## moov:trak:mdia:minf:stbl

- stco: 各チャンクの場所をファイルの先頭からのオフセットで示す。
- stsc: 各チャンクに含まれるサンプルの数を示す。
- stsz: 各サンプルの長さ。
- stts: 各サンプルの再生時間。

## stco: Chunk Offset

- 各チャンクの場所をファイルの先頭からのオフセットで示す。
- mdat Boxではないので注意。
- 故にメタデータが前の方にある場合に編集されると値が変わるから注意とある。
- いいことないよ…。mdat だけで完結させて欲しい…。
- entry_count: チャンクの数。

```e.g.
entry_count: 469
chunk_offset[0]: 48
chunk_offset[1]: 46071
chunk_offset[2]: 47385
chunk_offset[3]: 47775
```

```e.g.
entry_count: 469
chunk_offset[0]: 45700
chunk_offset[1]: 46727
chunk_offset[2]: 47482
chunk_offset[3]: 48355
```

## stsc: Sample To Chunk: 

- 各チャンクに含まれるサンプルの数を示す。
- sample_per_chunk/sample_description_indexが同じチャンクを省略できる。
- first_chunk: チャンクの塊の先頭のチャンクの番号。
    + the index of the first chunk in a track has the value 1 
- samples_per_chunk: 各チャンクの中のサンプルの数
- sample_description_index: Sample Description Boxの中のインデックス
    + an integer, gives the index of the sample entry that describes the samples in this chunk.
    + The index ranges from 1 to the number of sample entries in the Sample Description Box.

```e.g.
first_chunk[0]: 1
samples_per_chunk[0]: 1
first_chunk[1]: 2
samples_per_chunk[1]: 2
first_chunk[2]: 3
samples_per_chunk[2]: 1

| chunk# |nb_sample|
|========|=========|
|   001  |    1    |
|   002  |   1,2   |
|   003  |    1    |
```

```e.g.
first_chunk[0]: 1
samples_per_chunk[0]: 1
first_chunk[1]: 469
samples_per_chunk[1]: 2

| chunk# |nb_sample|
|========|=========|
|   001  |    1    |
|   002  |    1    |
|    :   |    :    |
|   468  |    1    |
|   469  |   1, 2  |
```

## stsz: Sample Size

- 各サンプルの長さ(バイト)。
- sample_size: 0ならば個別にサイズが記録されている。全てのサンプルのサイズが等しければここにサイズが記録される。
- sample_count: トラックに記録されているサンプルの数

```e.g.
sample_size: 0
sample_count: 750
entry_size[0]: 45652
entry_size[1]: 515
entry_size[2]: 141
entry_size[3]: 97
```

```e.g.
sample_size: 0
sample_count: 470
entry_size[0]: 371
entry_size[1]: 658
entry_size[2]: 293
entry_size[3]: 684
```

## stts: Decoding Time to Sample

- 各サンプルの再生時間(Decoding Time:DT)。
    + 合計はトラックの再生時間(mdhd:duration)に等しくなる。
    + Edit List は考慮しない。
- sample_deltaが同じDTを省略できる。
- DT(n+1) = DT(n) + STTS(n)
    + STTS(n) is the (uncompressed) table entry for sample n.
    + The DT axis has a zero origin;
- DT(i) = SUM(for j=0 to i-1 of delta(j))

```e.g.
entry_count: 1
sample_count: 750
sample_delta: 512
```

```e.g.
sample_count: 469
sample_delta: 1024
sample_count: 1
sample_delta: 768

|  DT(i) | duration|
|========|=========|
|   000  |  1024   |
|   001  |  1024   |
|    :   |    :    |
|   468  |  1024   |
|   469  |   768   |
```

## stss: Sync Sample

- トラック内の sync sample を示す。
- ビデオのみ？

    e.g.
    sample_number: 1
    sample_number: 251
    sample_number: 501

## ctts: Composition Time to Sample:

This box provides the offset between decoding time and composition time. In version 0 of this box

the decoding time must be less than the composition time, and the offsets are expressed as unsigned numbers such that

CT(n) = DT(n) + CTTS(n)

where CTTS(n) is the (uncompressed) table entry for sample n.

    entry_count: 748
    sample_count: 1
    sample_offset: 1024
    sample_count: 1
    sample_offset: 2560
    sample_count: 1
    sample_offset: 1024

```
file size: 635149
+ ftyp: 32
+ free: 8
+ mdat: 614623
+ moov: 20486
    + mvhd: 108
    + trak: 15959
        + tkhd: 92
        + edts: 36
            + elst: 28
        + mdia: 15823
            + mdhd: 32
            + hdlr: 45
            + minf: 15738
                + vmhd: 20
                + dinf: 36
                    + dref: 28
                + stbl: 15674
                    + stsd: 174
                    + stts: 24
                    + stss: 28
                    + ctts: 6000
                    + stsc: 4528
                    + stsz: 3020
                    + stco: 1892
    + trak: 4313
        + tkhd: 92
        + edts: 36
            + elst: 28
        + mdia: 4177
            + mdhd: 32
            + hdlr: 45
            + minf: 4092
                + smhd: 16
                + dinf: 36
                    + dref: 28
                + stbl: 4032
                    + stsd: 106
                    + stts: 32
                    + stsc: 40
                    + stsz: 1900
                    + stco: 1892
                    + sgpd: 26
                    + sbgp: 28
    + udta: 98
        + meta: 90
```

## H.264 stream

- Annex B: 0x00000001 で始まる。
- AVCC format: NALUの長さを含む4バイトのヘッダで始まる。

https://stackoverflow.com/questions/24884827/possible-locations-for-sequence-picture-parameter-sets-for-h-264-stream/24890903#24890903

TODO: ISO/IEC 14496-10 のチェック

