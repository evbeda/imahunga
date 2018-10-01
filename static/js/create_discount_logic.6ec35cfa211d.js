	$(document).ready(function(){
			$('#percentage-value').hide()
			$('#fixed-value').hide()
			$('#insert_discount_title').hide()
    		$('#discount_type').on('change',function() {
      			if ( this.value == 'fixed'){
      				$('#insert_discount_title').show()
        			$('#fixed-value').show()
					$('#percentage-value').hide()
					$('#discount_percentage').val('')
        		} else{
        			if(this.value == 'percentage'){
        				$('#insert_discount_title').show()
        				$('#percentage-value').show()
						$('#fixed-value').hide()
						$('#discount_fixed').val('')
        			}else{
        				$('#percentage-value').hide()
						$('#fixed-value').hide()
						$('#discount_fixed').val('')
						$('#insert_discount_title').hide()
						$('#discount_percentage').val('')
        			}
        		}
    		});
		});