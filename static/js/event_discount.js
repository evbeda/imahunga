$(function() {
    $('#discount_type_select').change(function(){
        $('#event_discount').hide();
        $('#ticket_discount').hide();
        $('#' + $(this).val()).show();
        $('#selected_value_discount_type').text($("#discount_type_select option:selected").text());
    });
});
$(function() {
    if( "{{has_discount}}" == 'Event' ){
        $('#ticket_discount').hide();
        $('#discount_type_select').val("event_discount")
    }else if( "{{has_discount}}" == 'Ticket' ){
        $('#event_discount').hide();
        $('#discount_type_select').val("ticket_discount")
    }else{
        $('#ticket_discount').hide();
        $('#event_discount').hide();
    }
    $('#selected_value_discount_type').text($("#discount_type_select option:selected").text());
});