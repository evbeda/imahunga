	$(document).ready(function(){
		$('#fixed_symbol').hide()
		$('#percentage_symbol').hide()
		$('#id_discount_type').on('change',function() {
			if (this.value == 'fixed'){
				$('#fixed_symbol').show()
				$('#percentage_symbol').hide()
			} else{
				if(this.value == 'percentage'){
					$('#percentage_symbol').show()
					$('#fixed_symbol').hide()
				}
			}
		});
	});