$(document).ready(function(){
    $("#event_name_box").hide()
    $("#event_name_box").css({'font-size':'1.3em'})
    $("#event_tickets").hide()
    $("#get_discount").hide()

    $("#btn_get_discount").click(function(event){
        event.preventDefault();
        if($("#get_discount").is(":visible")){
            $("#get_discount").hide()
        }else{
            $("#get_discount").show()
        }
    });
});
$(window).scroll(function(e){
      var $el = $('.fixedElement');
      var isPositionFixed = ($el.css('position') == 'fixed');
      if ($(this).scrollTop() > 450 && !isPositionFixed){
        $el.css({'position': 'fixed', 'top': '0px', 'width':'75%', 'box-shadow': '0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19)','z-index':'100'});
            $("#event_name_box").show()
            $("#event_tickets").show()
      }
      if ($(this).scrollTop() < 450 && isPositionFixed){
        $el.css({'position': 'static', 'top': '0px','width':'100%', 'box-shadow':'none' });
        $("#event_name_box").hide()
        $("#event_tickets").hide()
      }
});
