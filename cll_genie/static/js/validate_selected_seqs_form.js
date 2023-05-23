function validateForm(form_id) {
    var checkboxes = document.querySelectorAll('#' + form_id + ' input[type="checkbox"]');
    var checked = false;
    for (var i = 0; i < checkboxes.length; i++) {
      if (checkboxes[i].checked) {
        checked = true;
        break;
      }
    }
    if (checkboxes.length == 0) {
      checked = true;
    }
    if (!checked) {
      alert('Please select at least one option.');
      return false;
    }
    return true;
  }