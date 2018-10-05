	$(document).ready(function(){
		$('#fixed_symbol').hide()
		$('#percentage_symbol').hide()
		if ($('#id_discount_type').find(":selected")[0].value == 'fixed'){
				$('#fixed_symbol').show()
				$('#percentage_symbol').hide()
			} else{
				if($('#id_discount_type').find(":selected")[0].value == 'percentage'){
					$('#percentage_symbol').show()
					$('#fixed_symbol').hide()
				}
			}
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