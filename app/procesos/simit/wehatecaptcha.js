/**
 * Script de Referencia: Inyección y Gestión de qxCaptcha (SIMIT/FCM)
 * 
 * Este archivo es una transcripción del comportamiento del portal SIMIT para la gestión de 
 * desafíos de seguridad Proof-of-Work (PoW). 
 * 
 * FUNCIONAMIENTO TÉCNICO:
 * 1. Inicialización: Crea un formulario oculto (#wehatecaptchas) que dispara la carga del script 
 *    externo de qxCaptcha.
 * 2. Gestión de Cola: Utiliza el 'sessionStorage' para mantener una cola de hasta 5 desafíos 
 *    resueltos (questions).
 * 3. Intercepción: Sobrescribe el objeto global 'grecaptcha' para que las llamadas a 'execute()' 
 *    no busquen a Google, sino que consuman los retos resueltos por el worker de qxCaptcha.
 * 4. Serialización Crítica: En la línea 84, se observa cómo el script extrae (pop) un único 
 *    elemento de la cola y lo convierte en string antes de enviarlo al servidor.
 * 
 * NOTA: Este archivo no se ejecuta en el backend, sirve como documentación técnica y 
 * referencia para entender la lógica que el bot de Python emula en 'service.py'.
 */

$CONSTANTES.TipoDevice = {
    DESKTOP: $CONFIG.weHateCaptchaConfig.difficulty
};

$UTIL.isMobile = function () {
    return (/Android|webOS|iPhone|iPad|Mac|Macintosh|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
};

$UTIL.isReCaptchaEnabled = function () {
    return $CONFIG.weHateCaptchaConfig.enabled;
}

const customInitWeHateCaptcha = function (evt) {
    grecaptcha = {
        reset: function () { },
        execute: function (widgetReCaptcha) { evt(widgetReCaptcha) },
        oldEvt: evt
    };
    if ($CONFIG.weHateCaptchaConfig.enabled) {
        var xForm = document.querySelector("form#wehatecaptchas");
        if (xForm === null) {
            xForm = '<form id="wehatecaptchas" style="display:none"><button type="submit" difficulty="' + $CONFIG.weHateCaptchaConfig.difficulty + '">Submit</button></form>';
            $('body').append(xForm);
            importar($CONFIG.weHateCaptchaConfig.api);
            customInitWeHateCaptcha(evt);
            setInterval(function () {
                var whcQuestions = JSON.parse(sessionStorage.getItem('whcQuestions'));
                if ($.isEmptyObject(whcQuestions)) {
                    whcQuestions = { questions: [] };
                }
                if (whcQuestions.questions.length >= 5) {
                    return;
                } else {
                    if ('done' === whcFormButton.className) {
                        $("#whcModal").modal('hide');
                        whcQuestions.questions.unshift(JSON.parse(whcForm.querySelector(`input[name="captcha_verification"]`).value));
                        sessionStorage.setItem("whcQuestions", JSON.stringify(whcQuestions));
                        whcFormButton.classList.remove("done");
                        whcForm.querySelectorAll(`input[name="captcha_verification"]`).forEach(function (e) {
                            e.remove();
                        });
                        whcFormButton.click();
                    } else if (whcFormButton.disabled && whcQuestions.questions.length === 0) {
                        if ($.isEmptyObject(widgetReCaptcha)) {
                            var xModal = document.querySelector("div#whcModal");
                            if (xModal === null) {
                                $('body').append('<div class="modal fade" id="whcModal" tabindex="-1" role="dialog" aria-labelledby="exampleModalCenterTitle" aria-hidden="true" data-backdrop="static" data-keyboard="false" style="z-index:1000000">' +
                                    '<div class="modal-dialog modal-dialog-centered" role="document">' +
                                    '<div class="modal-content">' +
                                    '<div class="modal-body text-center py-4">' +
                                    '<p class="font-weight-bold mb-0 fs-17">¡Espera un momento!<p>' +
                                    '<p class="fs-16 px-4">Estamos realizando algunas validaciones para la seguridad de tu información.<p>' +
                                    '<div class="progress mt-3 mx-4">' +
                                    '<div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" style="width: 100%"></div>' +
                                    '</div>' +
                                    '</div>' +
                                    '</div>' +
                                    '</div>' +
                                    '</div>' +
                                    '</div>');
                            }
                            $("#whcModal").modal('show');

                        }
                    }
                }
            }, 500);
        } else {
            grecaptcha.execute = function () {
                var whcQuestions = JSON.parse(sessionStorage.getItem('whcQuestions'));
                if (!$.isEmptyObject(whcQuestions) && !$.isEmptyObject(whcQuestions.questions)) {
                    widgetReCaptcha = JSON.stringify(whcQuestions.questions.pop());
                    sessionStorage.setItem("whcQuestions", JSON.stringify(whcQuestions));
                    evt(widgetReCaptcha);
                } else {
                    setTimeout(function () {
                        grecaptcha.execute();
                    }, 1000);
                }
            };
        }
    } else {
        grecaptcha.reset = function () { };
        grecaptcha.execute = function (widgetReCaptcha) { evt(widgetReCaptcha) };
    }
};

const customRemoveWeHateCaptcha = function () {
};

var resetWidget = function (evt) {
    widgetReCaptcha = null;
};

initReCaptcha = customInitWeHateCaptcha;
removeReCaptcha = customRemoveWeHateCaptcha;
