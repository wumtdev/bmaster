// let mediaRecorder;
// let audioChunks = [];
// let recordWs;
// let listenWs;

document.getElementById('startListen').addEventListener('click', () => {
    const params = new URLSearchParams(location.search);
    const streamId = params.get('stream_id');
    document.getElementById("stream_id").textContent = streamId

    if (!streamId) return;

    listenWs = new WebSocket(`ws://localhost:8765?mode=listen&stream_id=${streamId}`);
    const audioContext = new AudioContext({ sampleRate: 48000 });
    let audioBufferQueue = [];

    listenWs.onmessage = async (event) => {
        if (typeof event.data === 'string') return;
        
        // Конвертация raw float32 в PCM-формат
        const float32Array = new Float32Array(await event.data.arrayBuffer());
        const pcmData = new Int16Array(float32Array.length);
        
        // Преобразование float32 (-1..1) в int16
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        // Создание WAV-чанка
        const wavBuffer = new ArrayBuffer(44 + pcmData.length * 2);
        const view = new DataView(wavBuffer);
        
        // Заголовок WAV
        writeString(view, 0, 'RIFF');
        view.setUint32(4, 36 + pcmData.length * 2, true);
        writeString(view, 8, 'WAVE');
        writeString(view, 12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, 48000, true);
        view.setUint32(28, 48000 * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(view, 36, 'data');
        view.setUint32(40, pcmData.length * 2, true);

        // Копирование PCM данных
        new Int16Array(wavBuffer, 44).set(pcmData);
        
        // Декодирование
        audioContext.decodeAudioData(wavBuffer).then(buffer => {
            const source = audioContext.createBufferSource();
            source.buffer = buffer;
            source.connect(audioContext.destination);
            source.start(0);
        }).catch(e => console.error('Decode error:', e));
    };

    document.getElementById('stopListen').disabled = false;
    document.getElementById('startListen').disabled = true;
});

// Вспомогательная функция для заголовка WAV
function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

document.getElementById('stopListen').addEventListener('click', () => {
    listenWs.close();
    document.getElementById('startListen').disabled = false;
    document.getElementById('stopListen').disabled = true;
})