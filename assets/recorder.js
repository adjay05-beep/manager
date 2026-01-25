// Global Recorder State
let mediaRecorder = null;
let audioChunks = [];

window.startJsRecording = async function () {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.start();
        // alert("Recording Started (JS)"); // Debug
        return "STARTED";
    } catch (err) {
        alert("Microphone Error: " + err);
        return "ERROR: " + err;
    }
};

window.stopJsRecordingAndUpload = async function (uploadUrl) {
    return new Promise((resolve, reject) => {
        if (!mediaRecorder) {
            alert("No Recorder Found");
            resolve("NO_RECORDER");
            return;
        }

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' }); // or audio/webm

            // Direct Upload to Signed URL
            try {
                // alert("Uploading " + audioBlob.size + " bytes...");
                const response = await fetch(uploadUrl, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'audio/wav' // Azure/Supabase might prefer precise mime
                    },
                    body: audioBlob
                });

                if (response.ok) {
                    // alert("Upload Success!");
                    resolve("SUCCESS");
                } else {
                    alert("Upload Failed: " + response.status);
                    resolve("UPLOAD_FAIL");
                }
            } catch (e) {
                alert("Network Error: " + e);
                resolve("NET_ERROR");
            }

            // Cleanup checks
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            mediaRecorder = null;
        };

        mediaRecorder.stop();
    });
};
