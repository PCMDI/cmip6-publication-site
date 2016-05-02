function doisearch(showform) {
    $('#loading').show();
    var doi = $("#doi-field").val();
    if (showform === true) {
        doi = ''
    }
    $.ajax({
        url: '/finddoi',
        method: 'GET',
        data: {'doi': doi},
        success: function(result){
            $('#loading').hide();
            $("#publication-form-wrapper").html(result);
            $.each($('#id_experiment li label'), function(index, element) {
                newelem = $('<input/>');
                $(newelem).attr('id', 'ensemble_'+index);
                $(newelem).attr('name', 'ensemble');
                $(element).after(newelem);
            });
            if (showform === true) {
                $('.alert.alert-warning').hide();
            }
        },
        error: function(jqxhr, status, error){
            $('#loading').hide();
            alert("Ajax Failed");
            console.log(jqxhr);
            console.log(status);
            console.log(error);
        }
    });
}

$(document).ready(function(){
    $('#loading').hide();
});

function submitPublication() {
    $.ajax({
        type: 'POST',
        url: '/new',
        data: $('form').serialize(),
        success: function(result){
            window.location.replace("/review");
        },
    }).fail(function($xhr) {
        var data = $.parseJSON($xhr.responseText);
        $('.pub_form').html(data.pub_form);
        $('#tabs div').filter(function() {
            return($(this)).css('display') == 'block';
        }).html(data.media_form);
        $('#author-form').html(data.auth_form);
    });

}
