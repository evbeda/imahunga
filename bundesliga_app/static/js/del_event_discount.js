$('#modal').on('show.bs.modal', function {{event_discount.id}}(event) {
    var modal = $('#modal')
    $.ajax({
        url: "{% url 'delete_discount' event_id event_discount.id %}",
        context: document.body
    }).done(function(response) {
        modal.html(response);
    });
});