let recordWs = null;
let audioContext = null;
let processor = null;
let mediaStream = null;

$('#recButton').addClass('notRec');

$('#recButton').click(async function() {
    if ($(this).hasClass('notRec')) {
        // Начало записи
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioContext = new AudioContext({ sampleRate: 48000 });
            const source = audioContext.createMediaStreamSource(mediaStream);
            
            recordWs = new WebSocket('ws://localhost:8765?mode=record');
            
            processor = audioContext.createScriptProcessor(1024, 1, 1);
            source.connect(processor);
            processor.connect(audioContext.destination);

            processor.onaudioprocess = (e) => {
                if (recordWs.readyState === WebSocket.OPEN) {
                    const data = e.inputBuffer.getChannelData(0);
                    recordWs.send(data.buffer);
                }
            };

            recordWs.onopen = () => {
                $(this).removeClass('notRec').addClass('Rec');
                $('#streamId').text('Recording...');
            };

            recordWs.onmessage = (event) => {
                if (event.data.startsWith('RECORD_START:')) {
                    const streamId = event.data.split(':')[1];
                    $('#streamId').text(`Stream ID: ${streamId}`);
                    document.getElementById("listenLink").textContent = `http://localhost:8080/listen.html?stream_id=${streamId}`
                }
            };

        } catch (err) {
            console.error('Error accessing microphone:', err);
            cleanupRecording();
        }
    } else {
        // Остановка записи
        if (recordWs) {
            recordWs.close();
        }
        cleanupRecording();
        $(this).removeClass('Rec').addClass('notRec');
        $('#streamId').text('Recording stopped');
    }
});

function cleanupRecording() {
    if (processor) {
        processor.disconnect();
        processor = null;
    }
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
}