from fastapi import HTTPException, status


class AppError(HTTPException):
    def __init__(self, status_code: int, code: str, detail: str, fields: dict | None = None):
        super().__init__(status_code=status_code, detail={"detail": detail, "code": code, "fields": fields or {}})


def unauthorized(code: str = "UNAUTHENTICATED", detail: str = "Credenciales inválidas") -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, code, detail)


def forbidden(code: str = "FORBIDDEN", detail: str = "Acceso denegado") -> AppError:
    return AppError(status.HTTP_403_FORBIDDEN, code, detail)


def not_found(entity: str) -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"{entity} no encontrado")


def conflict(detail: str, code: str = "CONFLICT") -> AppError:
    return AppError(status.HTTP_409_CONFLICT, code, detail)


def validation_error(detail: str, fields: dict | None = None) -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR", detail, fields)


def business_rule(detail: str, code: str = "BUSINESS_RULE") -> AppError:
    return AppError(status.HTTP_422_UNPROCESSABLE_ENTITY, code, detail)
