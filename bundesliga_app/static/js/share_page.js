$(document).ready(function(){
    $('[data-toggle="popover"]').popover({
        placement : 'bottom',
        html : true,
        content : '<input id="link" value={{ attendee_url }}></input> <button onclick="copy_text()"> <img class="img-w15-h15" src="{% static "images/copy.png" %}"> </button> <a href="{% url "landing_page_buyer" organizer.id %}" target="_blank">{% trans "View your page" %}</a>'
    });
});
function copy_text(){
    $("#link").select();
    document.execCommand("copy");
}