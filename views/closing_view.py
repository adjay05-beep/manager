import flet as ft
import asyncio
from utils.logger import log_debug
from views.components.custom_checkbox import CustomCheckbox
from views.components.app_header import AppHeader
from views.styles import AppColors, AppLayout

async def get_closing_controls(page: ft.Page, navigate_to):
    log_debug(f"Entering Closing View. User: {page.app_session.get('user_id')}")
    
    checklist = ft.Column([
        ft.Container(
            content=CustomCheckbox(label="주방 가스 밸브 차단 확인", label_style=ft.TextStyle(color=AppColors.TEXT_PRIMARY)),
            padding=15, bgcolor=AppColors.SURFACE_VARIANT, border_radius=10
        ),
        ft.Container(
            content=CustomCheckbox(label="홀 에어컨 및 조명 OFF 확인", label_style=ft.TextStyle(color=AppColors.TEXT_PRIMARY)),
            padding=15, bgcolor=AppColors.SURFACE_VARIANT, border_radius=10
        ),
    ], spacing=10)
    
    is_confirmed = ft.Ref[CustomCheckbox]()
    complete_button = ft.Ref[ft.Button]()

    async def toggle_confirm(e):
        if is_confirmed.current.value:
            complete_button.current.disabled = False
        else:
            complete_button.current.disabled = True
        page.update()

    async def go_home(e):
        await navigate_to("home")

    header = AppHeader(
        title_text="마감 체크리스트",
        on_back_click=lambda e: asyncio.create_task(go_home(e))
    )

    return [
        ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                bgcolor=AppColors.BG_LIGHT if page.theme_mode == ft.ThemeMode.LIGHT else AppColors.BG_DARK,
                content=ft.Column([
                    header,
                    ft.Container(
                        padding=AppLayout.CONTENT_PADDING,
                        expand=True,
                        content=ft.Column([
                            ft.Text("Safety Checklist", color=AppColors.TEXT_SECONDARY, size=14),
                            checklist,
                            ft.Container(height=40),
                            CustomCheckbox(
                                ref=is_confirmed,
                                label="마감 확인 (위 내용을 모두 확인했습니다)",
                                value=False,
                                on_change=lambda e: asyncio.create_task(toggle_confirm(e)),
                                label_style=ft.TextStyle(color=AppColors.TEXT_PRIMARY)
                            ),
                            ft.Button(
                                ref=complete_button,
                                content=ft.Text("점검 완료 및 퇴근"),
                                on_click=lambda e: asyncio.create_task(go_home(e)),
                                width=float("inf"), height=50,
                                disabled=True,
                                style=ft.ButtonStyle(
                                    color="white",
                                    bgcolor=AppColors.SUCCESS,
                                    shape=ft.RoundedRectangleBorder(radius=10)
                                )
                            )
                        ], scroll=ft.ScrollMode.AUTO)
                    )
                ], spacing=0)
            )
        )
    ]

