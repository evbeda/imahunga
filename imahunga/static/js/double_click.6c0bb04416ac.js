$(document).ready(function(){
	$('#submit_btn').on('click',function()
	  {
	    $(this).val('Please wait ...')
	      .attr('disabled','disabled');
	       $('#discount_form').submit();
	  });
});
