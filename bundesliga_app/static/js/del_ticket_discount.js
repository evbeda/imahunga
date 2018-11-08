$('#modal').on('show.bs.modal', function {{ticket_type.discount.id}}(event) {
    var modal = $('#modal')
    $.ajax({
        url: "{% url 'delete_discount' event_id ticket_type.discount.id %}",
        context: document.body
    }).done(function(response) {
        modal.html(response);
    });
});