// JavaScript code to update the options in the receptorOrLocusType dropdown based on the species selected
function updateLocus() {
    // Get the selected value of the species dropdown
    var species = document.getElementById("species").value;
  
    // Get the receptorOrLocusType dropdown and remove all its options
    var locusDropDown = document.getElementById("receptorOrLocusType");
    locusDropDown.innerHTML = "";

    // Define a dictionary of receptor loci for each species
    var receptors_loci_Dict = {
      "human": ['IG', 'IGH', 'IGK', 'IGL', 'TR', 'TRA', 'TRB', 'TRG', 'TRD'],
      "mouse": ['IG', 'IGH', 'IGK', 'IGL', 'TR', 'TRA', 'TRB', 'TRG', 'TRD'],
      "mas-night-monkey": ['TR', 'TRA', 'TRB', 'TRG', 'TRD'],
      "bovine": ['IG', 'IGH', 'IGK', 'IGL', 'TR', 'TRA', 'TRB', 'TRG', 'TRD'],
      "camel": ['IGK', 'TR', 'TRA', 'TRB', 'TRG', 'TRD'],
      "dog": ['IG', 'IGH', 'IGK', 'IGL', 'TR', 'TRA', 'TRB', 'TRG', 'TRD'],
      "goat": ['IG', 'IGK', 'IGL'],
      "chondrichthyes": ['IG', 'IGH'],
      "zebrafish": ['IG', 'IGH', 'IGI', 'TR', 'TRA', 'TRD'],
      "horse": ['IG', 'IGK', 'IGH'],
      "cat": ['IG', 'IGL', 'IGK', 'TR', 'TRA', 'TRB', 'TRD', 'TRG'],
      "cod": ['IGH'],
      "chicken": ['IG', 'IGH', 'IGL'],
      "gorilla": ['IG', 'IGH', 'IGK', 'TR', 'TRG'],
      "naked-mole-rat": ['TR', 'TRA', 'TRB', 'TRD', 'TRG'],
      "catfish": ['IGH'],
      "lemur": ['IG', 'IGH', 'IGK'],
      "crab-eating-macaque": ['IGH', 'TRB'],
      "rhesus-monkey": ['IG', 'IGH', 'IGK', 'IGL', 'TR', 'TRA', 'TRB', 'TRD', 'TRG'],
      "ferret": ['TRB'],
      "nonhuman-primates": ['TR', 'TRA', 'TRB', 'TRG', 'TRD'],
      "platypus": ['IG', 'IGH'],
      "rabbit": ['IG', 'IGH', 'IGK', 'IGL', 'TR', 'TRA', 'TRB', 'TRG', 'TRD'],
      "sheep": ['IG', 'IGH', 'IGK', 'IGL', 'TR', 'TRA', 'TRB', 'TRD'],
      "pongo": ['IGK'],
      "rat": ['IG', 'IGH', 'IGK', 'IGL'],
      "salmon": ['IGH'],
      "pig": ['IG', 'IGH', 'IGK', 'IGL', 'TR', 'TRB'],
      "teleostei": ['IG', 'IGH', 'IGI'],
      "dolphin": ['TR', 'TRA', 'TRD', 'TRG'],
      "alpaca": ['IG', 'IGH']
    };

    // Create an array of receptors_loci options based on the selected species
    var receptors_loci = receptors_loci_Dict[species];
  
    for (var i = 0; i < receptors_loci.length; i++) {
      var option = document.createElement("option");
      option.text = receptors_loci[i];
      option.value = receptors_loci[i];
      locusDropDown.add(option);
    }
  }