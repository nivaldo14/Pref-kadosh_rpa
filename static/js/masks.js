// Simple vanilla JS input masks

function formatCPF(cpf) {
    cpf = cpf.replace(/\D/g, ''); // Remove all non-numeric characters
    cpf = cpf.replace(/(\d{3})(\d)/, '$1.$2');
    cpf = cpf.replace(/(\d{3})(\d)/, '$1.$2');
    cpf = cpf.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    return cpf;
}

function formatTelefone(telefone) {
    telefone = telefone.replace(/\D/g, ''); // Remove all non-numeric characters
    if (telefone.length > 10) {
        // (XX) XXXXX-XXXX
        telefone = telefone.replace(/^(\d\d)(\d{5})(\d{4}).*/, '($1) $2-$3');
    } else if (telefone.length > 5) {
        // (XX) XXXX-XXXX
        telefone = telefone.replace(/^(\d\d)(\d{4})(\d{0,4}).*/, '($1) $2-$3');
    } else if (telefone.length > 2) {
        // (XX) XXXX
        telefone = telefone.replace(/^(\d\d)(\d{0,5}).*/, '($1) $2');
    } else {
        telefone = telefone.replace(/^(\d*)/, '($1');
    }
    return telefone;
}


document.addEventListener('DOMContentLoaded', function() {
    // Mask for Motorista Add form
    const cpfInput = document.getElementById('motorista-cpf');
    if (cpfInput) {
        cpfInput.addEventListener('input', (e) => {
            e.target.value = formatCPF(e.target.value);
        });
    }

    const telInput = document.getElementById('motorista-telefone');
    if (telInput) {
        telInput.addEventListener('input', (e) => {
            e.target.value = formatTelefone(e.target.value);
        });
    }

    // Mask for Motorista Edit form
    const cpfInputEdit = document.getElementById('motorista-cpf-edit');
    if (cpfInputEdit) {
        cpfInputEdit.addEventListener('input', (e) => {
            e.target.value = formatCPF(e.target.value);
        });
    }
    
    const telInputEdit = document.getElementById('motorista-telefone-edit');
    if (telInputEdit) {
        telInputEdit.addEventListener('input', (e) => {
            e.target.value = formatTelefone(e.target.value);
        });
    }

    // Mask for Admin Robo form
    const telRoboInput = document.getElementById('robo-telefone');
    if (telRoboInput) {
        telRoboInput.addEventListener('input', (e) => {
            e.target.value = formatTelefone(e.target.value);
        });
    }
});
