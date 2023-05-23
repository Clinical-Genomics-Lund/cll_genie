function displaySelectedFile(input) {
    const selectedFileSpan = document.getElementById('selected-file');
    if (input.files.length > 0) {
        selectedFileSpan.textContent = 'Selected file: ' + input.files[0].name;
    } else {
        selectedFileSpan.textContent = '';
    }
}
