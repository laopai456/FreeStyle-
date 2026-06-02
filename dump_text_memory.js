/**
 * dump_text_memory.js — 从内存 dump FreeStyle.exe 的 .text 段（已解压）
 * 保存到文件用于后续静态分析
 */
'use strict';

var base = Module.findBaseAddress("FreeStyle.exe");
if (!base) {
    console.log("FreeStyle.exe not loaded!");
    send({type: "error", msg: "FreeStyle.exe not loaded"});
} else {
    // .text 段: VA=0x1000, size=0x280B000 (42MB)
    var TEXT_VA = 0x1000;
    var TEXT_SIZE = 0x280B000;
    var textBase = base.add(TEXT_VA);
    
    send({type: "info", msg: "FreeStyle.exe base: " + base});
    send({type: "info", msg: ".text section at: " + textBase + " size: " + TEXT_SIZE});
    
    // 分块读取（42MB 太大，分 1MB 块）
    var CHUNK_SIZE = 0x100000; // 1MB
    var totalChunks = Math.ceil(TEXT_SIZE / CHUNK_SIZE);
    send({type: "info", msg: "Reading " + totalChunks + " chunks of " + (CHUNK_SIZE/1024) + "KB..."});
    
    var allData = [];
    for (var i = 0; i < totalChunks; i++) {
        var offset = i * CHUNK_SIZE;
        var size = Math.min(CHUNK_SIZE, TEXT_SIZE - offset);
        try {
            var data = textBase.add(offset).readByteArray(size);
            allData.push(data);
        } catch (e) {
            send({type: "error", msg: "Chunk " + i + " read failed: " + e});
        }
    }
    
    send({type: "data", chunks: totalChunks, totalSize: TEXT_SIZE});
    
    // 合并并保存到文件（通过 send 逐块发送）
    for (var i = 0; i < allData.length; i++) {
        if (allData[i]) {
            send({
                type: "dump", 
                chunk: i, 
                offset: i * CHUNK_SIZE,
                data: Array.from(new Uint8Array(allData[i])),
                total: totalChunks
            });
        }
    }
    
    send({type: "done", msg: "Dump complete"});
}