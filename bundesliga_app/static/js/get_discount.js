var input_added = 2
$(document).ready(function(){
    var form_options = {
        target: '#get_discount_form',
        dataType: 'json',
        success: function(response) {
            window.location.href=response.url
            $("#loading").hide()
            $("#submit_btn").show()
        },
        error: function(response){
            document.getElementById('errors').innerHTML=$($.parseHTML(response.responseText)).find("#errors_form")[1].innerHTML;
            $('#retry').show();
            $('#submit_btn').val('Retry');
            $("#loading").hide()
            $("#submit_btn").show()
            console.log(response)
        }
    }
    $('#get_discount_form').ajaxForm(form_options);
    var max_member_number = 10

    $("#loading").hide()

    $("#submit_btn").click(function(){
        var invalidNumber = false
        if(!($('[name=member_number_1]').val() == "")){
            for (i = 2; i < input_added; i++) {
                if($('[name=member_number_' + i +']').val() == ""){
                    invalidNumber = true
                }
            }
            if(!invalidNumber){
                $("#submit_btn").hide()
                $("#loading").show()
                $("#retry").hide()
            }
        }

    });

    $("#add_field").on('click',function(){
        if(input_added <= max_member_number){
            var member_input = '<div class="input-group input-group-lg mx-auto width-50-percentage"><input name="member_number_' + input_added+ '" type="number" class="form-control mt-3 input_added" placeholder="Insert your member number here" required/><input name="remove_number_' + input_added + '" type="button" value="X" onclick="remove('+ input_added +')"/></div>';
            // console.log(member_input)
            $("#form-members-numbers").append(member_input)
            input_added += 1
        }else{
            alert("You can only add up to 10 member's numbers")
        }
    });
});
function remove(input_to_delete){
    console.log(input_to_delete)
    $('[name=member_number_' + input_to_delete + ']').val('')
    $('[name=member_number_' + input_to_delete + ']').remove()
    $('[name=remove_number_' + input_to_delete + ']').remove()
    for(i=input_to_delete+1; i<= input_added; i++){
        $('[name=member_number_' + i + ']').attr('name', 'member_number_' + (i-1))
        $('[name=remove_number_' + i + ']').attr('onclick', 'remove(' + (i-1) + ')')
        $('[name=remove_number_' + i + ']').attr('name', 'remove_number_' + (i-1))
        input_added -= 1
    }
}